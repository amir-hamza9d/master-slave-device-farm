import asyncio
import websockets
import json
import logging
import subprocess
import argparse
import sys
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('farm-device-executor.log')
    ]
)
logger = logging.getLogger("FarmDeviceExecutor")

class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    EXECUTING = "executing"
    ERROR = "error"

@dataclass
class DeviceInfo:
    device_id: str
    model: str
    android_version: str
    screen_width: int
    screen_height: int
    status: DeviceStatus
    last_seen: float
    error_count: int = 0
    websocket: Optional[object] = None

class FarmDeviceManager:
    def __init__(self, central_server_url: str = "ws://127.0.0.1:8765/farm", debug: bool = False):
        self.central_server_url = central_server_url
        self.debug = debug
        self.devices: Dict[str, DeviceInfo] = {}
        self.master_resolution: Optional[Dict[str, int]] = None
        self.pending_taps: Dict[str, Dict[str, int]] = {}  # Track tap_press for each device
        self.max_retry_attempts = 5
        self.retry_delay = 5
        self.device_check_interval = 10
        self.connection_timeout = 30
        self.master_device: Optional[str] = None # To store the ID of the master device

    async def discover_devices(self) -> List[str]:
        """Discover all connected Android devices via ADB"""
        try:
            logger.info("🔍 Discovering connected devices...")
            process = await asyncio.create_subprocess_exec(
                'adb', 'devices', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ADB devices command failed: {stderr.decode('utf-8')}")
                return []
            
            output = stdout.decode('utf-8').strip()
            lines = output.split('\n')[1:]  # Skip header
            
            devices = []
            for line in lines:
                if 'device' in line and line.strip():
                    # Split by whitespace and take the first part as device_id
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == 'device':
                        device_id = parts[0]
                        devices.append(device_id)
            
            logger.info(f"📱 Discovered {len(devices)} device(s): {devices}")
            return devices
            
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            return []

    async def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get detailed information about a specific device"""
        try:
            logger.debug(f"Getting info for device: {device_id}")
            
            # Get device model
            model_process = await asyncio.create_subprocess_exec(
                'adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            model_stdout, _ = await model_process.communicate()
            model = model_stdout.decode('utf-8').strip() or "Unknown"
            
            # Get Android version
            version_process = await asyncio.create_subprocess_exec(
                'adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            version_stdout, _ = await version_process.communicate()
            version = version_stdout.decode('utf-8').strip() or "Unknown"
            
            # Get screen resolution
            resolution = await self.get_screen_resolution(device_id)
            
            device_info = DeviceInfo(
                device_id=device_id,
                model=model,
                android_version=version,
                screen_width=resolution["width"],
                screen_height=resolution["height"],
                status=DeviceStatus.DISCONNECTED,
                last_seen=time.time()
            )
            
            logger.info(f"📱 Device Info - {device_id}: {model} (Android {version}, {resolution['width']}x{resolution['height']})")
            return device_info
            
        except Exception as e:
            logger.error(f"Error getting device info for {device_id}: {e}")
            return None

    async def get_screen_resolution(self, device_id: str) -> Dict[str, int]:
        """Get device screen resolution"""
        try:
            process = await asyncio.create_subprocess_exec(
                'adb', '-s', device_id, 'shell', 'wm', 'size',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            output = stdout.decode('utf-8').strip()
            if 'Physical size:' in output:
                size_part = output.split('Physical size:')[1].strip()
                width, height = map(int, size_part.split('x'))
                return {"width": width, "height": height}
            else:
                logger.warning(f"Could not parse screen resolution for {device_id}: {output}")
                return {"width": 1080, "height": 1920}  # Default fallback
                
        except Exception as e:
            logger.error(f"Error getting screen resolution for {device_id}: {e}")
            return {"width": 1080, "height": 1920}  # Default fallback

    def scale_coordinates(self, x: int, y: int, device_info: DeviceInfo) -> Tuple[int, int]:
        """Scale coordinates from master device to farm device"""
        if not self.master_resolution or "input_x_max" not in self.master_resolution or "input_y_max" not in self.master_resolution:
            logger.warning(f"Master resolution or input max values not available for scaling. Using raw coordinates: ({x}, {y})")
            return x, y  # No scaling if master resolution or input max unknown
        
        master_input_x_max = self.master_resolution["input_x_max"]
        master_input_y_max = self.master_resolution["input_y_max"]

        if master_input_x_max == 0 or master_input_y_max == 0:
            logger.error(f"Master input max values are zero, cannot scale. Using raw coordinates: ({x}, {y})")
            return x, y # Avoid division by zero

        # Scale from master's raw input range to master's pixel resolution
        # Then scale from master's pixel resolution to farm device's pixel resolution
        # Combined: (raw_x / master_input_x_max) * master_pixel_width * (farm_pixel_width / master_pixel_width)
        # Simplified: (raw_x / master_input_x_max) * farm_pixel_width
        
        scaled_x = int((x / master_input_x_max) * device_info.screen_width)
        scaled_y = int((y / master_input_y_max) * device_info.screen_height)
        
        logger.debug(f"Scaling coordinates for {device_info.device_id}: ({x}, {y}) [raw] -> ({scaled_x}, {scaled_y}) [farm_pixel]. "
                    f"Master Input Max: {master_input_x_max}x{master_input_y_max}, "
                    f"Farm Device Res: {device_info.screen_width}x{device_info.screen_height}")
        
        return scaled_x, scaled_y

    async def execute_tap(self, x: int, y: int, device_info: DeviceInfo) -> bool:
        """Execute tap action on device"""
        try:
            device_info.status = DeviceStatus.EXECUTING
            
            cmd = ['adb', '-s', device_info.device_id, 'shell', 'input', 'tap', str(x), str(y)]
            logger.debug(f"{device_info.device_id}: Executing command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()

            if process.returncode == 0:
                logger.info(f"✅ {device_info.device_id}: Executed tap at ({x}, {y})")
                if stdout_str:
                    logger.debug(f"{device_info.device_id}: Tap stdout: {stdout_str}")
                # Show clean execution in normal mode, detailed in debug mode
                if self.debug:
                    print(f"🎯 TAP EXECUTED on {device_info.device_id}: ({x}, {y})")
                else:
                    print(f"✅ {device_info.device_id}: TAP executed")
                device_info.status = DeviceStatus.CONNECTED
                device_info.error_count = 0
                return True
            else:
                logger.error(f"❌ {device_info.device_id}: Failed to execute tap (Return Code: {process.returncode})")
                if stdout_str:
                    logger.error(f"{device_info.device_id}: Tap stdout: {stdout_str}")
                if stderr_str:
                    logger.error(f"{device_info.device_id}: Tap stderr: {stderr_str}")
                device_info.error_count += 1
                device_info.status = DeviceStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Error executing tap on {device_info.device_id}: {e}")
            device_info.error_count += 1
            device_info.status = DeviceStatus.ERROR
            return False

    async def execute_key_press(self, key_code: str, device_info: DeviceInfo) -> bool:
        """Execute key press action on device"""
        try:
            device_info.status = DeviceStatus.EXECUTING
            
            # Convert key codes to Android key event codes
            key_mapping = {
                'KEY_BACK': '4',
                'KEY_HOME': '3',
                'KEY_MENU': '82',
                'KEY_POWER': '26',
                'KEY_VOLUMEUP': '24',
                'KEY_VOLUMEDOWN': '25',
                'BTN_BACK': '4',
                'KEY_ENTER': '66',
                'KEY_SPACE': '62',
            }
            
            android_key_code = key_mapping.get(key_code, key_code)
            
            cmd = ['adb', '-s', device_info.device_id, 'shell', 'input', 'keyevent', android_key_code]
            logger.debug(f"{device_info.device_id}: Executing command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()

            if process.returncode == 0:
                logger.info(f"✅ {device_info.device_id}: Executed key press: {key_code} ({android_key_code})")
                if stdout_str:
                    logger.debug(f"{device_info.device_id}: Key press stdout: {stdout_str}")
                # Show clean execution in normal mode, detailed in debug mode
                if self.debug:
                    print(f"⌨️ KEY EXECUTED on {device_info.device_id}: {key_code}")
                else:
                    print(f"✅ {device_info.device_id}: KEY executed")
                device_info.status = DeviceStatus.CONNECTED
                device_info.error_count = 0
                return True
            else:
                logger.error(f"❌ {device_info.device_id}: Failed to execute key press (Return Code: {process.returncode})")
                if stdout_str:
                    logger.error(f"{device_info.device_id}: Key press stdout: {stdout_str}")
                if stderr_str:
                    logger.error(f"{device_info.device_id}: Key press stderr: {stderr_str}")
                device_info.error_count += 1
                device_info.status = DeviceStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Error executing key press on {device_info.device_id}: {e}")
            device_info.error_count += 1
            device_info.status = DeviceStatus.ERROR
            return False

    async def execute_text_input(self, text: str, device_info: DeviceInfo) -> bool:
        """Execute text input action on device"""
        try:
            device_info.status = DeviceStatus.EXECUTING
            
            # Escape special characters for shell
            escaped_text = text.replace(' ', '%s').replace('&', '\\&').replace('"', '\\"')
            
            cmd = ['adb', '-s', device_info.device_id, 'shell', 'input', 'text', escaped_text]
            logger.debug(f"{device_info.device_id}: Executing command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode('utf-8').strip()
            stderr_str = stderr.decode('utf-8').strip()

            if process.returncode == 0:
                logger.info(f"✅ {device_info.device_id}: Executed text input: '{text}'")
                if stdout_str:
                    logger.debug(f"{device_info.device_id}: Text input stdout: {stdout_str}")
                # Show clean execution in normal mode, detailed in debug mode
                if self.debug:
                    print(f"📝 TEXT EXECUTED on {device_info.device_id}: '{text}'")
                else:
                    print(f"✅ {device_info.device_id}: TEXT executed")
                device_info.status = DeviceStatus.CONNECTED
                device_info.error_count = 0
                return True
            else:
                logger.error(f"❌ {device_info.device_id}: Failed to execute text input (Return Code: {process.returncode})")
                if stdout_str:
                    logger.error(f"{device_info.device_id}: Text input stdout: {stdout_str}")
                if stderr_str:
                    logger.error(f"{device_info.device_id}: Text input stderr: {stderr_str}")
                device_info.error_count += 1
                device_info.status = DeviceStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Error executing text input on {device_info.device_id}: {e}")
            device_info.error_count += 1
            device_info.status = DeviceStatus.ERROR
            return False

    async def process_action(self, action_data: dict, device_info: DeviceInfo):
        """Process received action from central server for a specific device"""
        action = action_data.get('action')
        device_id = device_info.device_id
        
        try:
            if action == 'tap_press':
                # Store tap press, wait for tap_release to execute complete tap
                x, y = action_data.get('x'), action_data.get('y')
                if x is not None and y is not None:
                    # Scale coordinates
                    x, y = self.scale_coordinates(x, y, device_info)
                    self.pending_taps[device_id] = {'x': x, 'y': y}
                    logger.debug(f"{device_id}: Stored tap_press at ({x}, {y})")
                    # Only show detailed tap press storage in debug mode
                    if self.debug:
                        print(f"👆 TAP PRESS STORED on {device_id}: ({x}, {y})")
            
            elif action == 'tap_release':
                # Execute the complete tap action
                if device_id in self.pending_taps:
                    pending = self.pending_taps[device_id]
                    await self.execute_tap(pending['x'], pending['y'], device_info)
                    del self.pending_taps[device_id]
                else:
                    # Fallback: execute tap at release coordinates
                    x, y = action_data.get('x'), action_data.get('y')
                    if x is not None and y is not None:
                        x, y = self.scale_coordinates(x, y, device_info)
                        await self.execute_tap(x, y, device_info)
            
            elif action == 'key_press':
                key_code = action_data.get('key_code')
                if key_code:
                    await self.execute_key_press(key_code, device_info)
            
            elif action == 'key_release':
                # We handle key press/release as single action, so ignore release
                logger.debug(f"{device_id}: Ignoring key_release for {action_data.get('key_code')}")
            
            elif action == 'text_input':
                text = action_data.get('text')
                if text:
                    await self.execute_text_input(text, device_info)
            
            elif action == 'master_resolution_update':
                resolution = action_data.get('resolution')
                if resolution and isinstance(resolution, dict) and 'width' in resolution and 'height' in resolution:
                    self.master_resolution = resolution
                    logger.info(f"{device_id}: Received master resolution update: {resolution['width']}x{resolution['height']}")
                else:
                    logger.warning(f"{device_id}: Invalid master_resolution_update received: {action_data}")
            
            else:
                logger.warning(f"{device_id}: Unknown action: {action}")
                
            device_info.last_seen = time.time()
            
        except Exception as e:
            logger.error(f"Error processing action {action} on {device_id}: {e}")
            device_info.error_count += 1
            device_info.status = DeviceStatus.ERROR

    async def connect_websocket(self) -> Optional[object]:
        """Connect to central server with retry logic"""
        for attempt in range(self.max_retry_attempts):
            try:
                logger.info(f"🔌 Connecting to central server (attempt {attempt + 1}/{self.max_retry_attempts})")
                websocket = await asyncio.wait_for(
                    websockets.connect(self.central_server_url),
                    timeout=self.connection_timeout
                )
                logger.info(f"✅ Connected to central server: {self.central_server_url}")
                return websocket
                
            except asyncio.TimeoutError:
                logger.error(f"❌ Connection timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"❌ Connection failed (attempt {attempt + 1}): {e}")
            
            if attempt < self.max_retry_attempts - 1:
                logger.info(f"⏳ Retrying in {self.retry_delay} seconds...")
                await asyncio.sleep(self.retry_delay)
        
        logger.error("❌ Failed to connect after all retry attempts")
        return None

    async def send_device_info(self, websocket, device_info: DeviceInfo):
        """Send device information to central server"""
        try:
            info_message = {
                "action": "device_info",
                "role": "farm",
                "device_info": {
                    "id": device_info.device_id,
                    "model": device_info.model,
                    "android_version": device_info.android_version,
                    "screen_width": device_info.screen_width,
                    "screen_height": device_info.screen_height
                }
            }
            await websocket.send(json.dumps(info_message))
            logger.info(f"📤 Sent device info for {device_info.device_id}: {device_info.model}")
            
        except Exception as e:
            logger.error(f"Failed to send device info for {device_info.device_id}: {e}")

    async def handle_device_connection(self, device_info: DeviceInfo):
        """Handle WebSocket connection for a single device"""
        retry_count = 0
        
        while retry_count < self.max_retry_attempts:
            try:
                device_info.status = DeviceStatus.CONNECTING
                websocket = await self.connect_websocket()
                
                if not websocket:
                    retry_count += 1
                    continue
                
                device_info.websocket = websocket
                device_info.status = DeviceStatus.CONNECTED
                device_info.error_count = 0
                
                # Send device info to central server
                await self.send_device_info(websocket, device_info)
                
                logger.info(f"🤖 {device_info.device_id}: Ready to receive actions")
                print(f"🔥 FARM DEVICE READY: {device_info.device_id} ({device_info.model})")
                
                # Listen for actions
                async for message in websocket:
                    try:
                        action_data = json.loads(message)
                        logger.info(f"{device_info.device_id}: Received action: {action_data}") # Changed to INFO for visibility

                        # Print received action for visibility - clean in normal mode, detailed in debug mode
                        action_type = action_data.get('action', 'unknown')
                        if self.debug:
                            if 'x' in action_data and 'y' in action_data:
                                print(f"📡 RECEIVED on {device_info.device_id}: {action_type} at ({action_data['x']}, {action_data['y']})")
                            else:
                                print(f"📡 RECEIVED on {device_info.device_id}: {action_type}")
                        else:
                            # Clean, simple received action log for normal mode
                            if action_type in ['tap_press', 'tap_release']:
                                print(f"📱 {device_info.device_id}: Received TAP action")
                            elif action_type in ['key_press', 'key_release']:
                                print(f"📱 {device_info.device_id}: Received KEY action")
                            elif action_type == 'text_input':
                                print(f"📱 {device_info.device_id}: Received TEXT action")
                            elif action_type != 'master_resolution_update':  # Don't show resolution updates in normal mode
                                print(f"📱 {device_info.device_id}: Received {action_type.upper()} action")
                        
                        # Process the action
                        await self.process_action(action_data, device_info)
                        
                    except json.JSONDecodeError:
                        logger.error(f"{device_info.device_id}: Received invalid JSON: {message}")
                    except Exception as e:
                        logger.error(f"{device_info.device_id}: Error processing action: {e}")
                        device_info.error_count += 1
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"🔌 {device_info.device_id}: Connection closed")
                device_info.status = DeviceStatus.DISCONNECTED
            except Exception as e:
                logger.error(f"❌ {device_info.device_id}: Connection error: {e}")
                device_info.status = DeviceStatus.ERROR
                device_info.error_count += 1
            
            retry_count += 1
            if retry_count < self.max_retry_attempts:
                logger.info(f"⏳ {device_info.device_id}: Reconnecting in {self.retry_delay} seconds... (attempt {retry_count + 1})")
                await asyncio.sleep(self.retry_delay)
            else: # Added else block for final error message
                logger.error(f"❌ {device_info.device_id}: Max retry attempts reached, giving up")
                device_info.status = DeviceStatus.ERROR

    async def monitor_device_health(self):
        """Monitor device health and connectivity"""
        while True:
            try:
                current_time = time.time()
                
                # Check device connectivity
                for device_id, device_info in self.devices.items():
                    if device_info.status == DeviceStatus.ERROR and device_info.error_count > 3:
                        logger.warning(f"⚠️ {device_id}: High error count ({device_info.error_count}), may need attention")
                    
                    if current_time - device_info.last_seen > 60:  # 1 minute timeout
                        logger.warning(f"⚠️ {device_id}: No activity for {int(current_time - device_info.last_seen)} seconds")
                
                # Rediscover devices periodically
                current_devices = await self.discover_devices()
                
                # Filter out the master device from the discovered list
                # The 'master_device' attribute is set in the 'run' method
                filtered_devices = [d for d in current_devices if d != self.master_device]

                # Add new devices
                for device_id in filtered_devices:
                    if device_id not in self.devices:
                        logger.info(f"🆕 New farm device detected: {device_id}")
                        device_info = await self.get_device_info(device_id)
                        if device_info:
                            self.devices[device_id] = device_info
                            # Start connection for new device
                            asyncio.create_task(self.handle_device_connection(device_info))
                
                # Mark disconnected devices
                for device_id in list(self.devices.keys()):
                    if device_id not in filtered_devices:
                        logger.warning(f"📱 Farm device disconnected: {device_id}")
                        self.devices[device_id].status = DeviceStatus.DISCONNECTED
                
                await asyncio.sleep(self.device_check_interval)
                
            except Exception as e:
                logger.error(f"Error in device health monitor: {e}")
                await asyncio.sleep(self.device_check_interval)

    async def print_status(self):
        """Print periodic status updates"""
        while True:
            try:
                await asyncio.sleep(30)  # Print status every 30 seconds
                
                total_devices = len(self.devices)
                connected_devices = sum(1 for d in self.devices.values() if d.status == DeviceStatus.CONNECTED)
                error_devices = sum(1 for d in self.devices.values() if d.status == DeviceStatus.ERROR)
                
                print(f"\n📊 FARM STATUS: {connected_devices}/{total_devices} devices connected, {error_devices} errors")
                
                for device_id, device_info in self.devices.items():
                    status_emoji = {
                        DeviceStatus.CONNECTED: "✅",
                        DeviceStatus.CONNECTING: "🔄",
                        DeviceStatus.DISCONNECTED: "❌",
                        DeviceStatus.EXECUTING: "⚡",
                        DeviceStatus.ERROR: "🚨"
                    }
                    emoji = status_emoji.get(device_info.status, "❓")
                    print(f"  {emoji} {device_id}: {device_info.model} ({device_info.status.value})")
                
                print()
                
            except Exception as e:
                logger.error(f"Error printing status: {e}")

    def prompt_for_master_device(self, available_devices: List[str]) -> Optional[str]:
        """Prompt user to specify which device is the master (to exclude from farm)"""
        print("\n" + "="*60)
        print("🎯 MASTER DEVICE EXCLUSION")
        print("="*60)
        print("Please specify which device is being used as the MASTER device.")
        print("This device will be EXCLUDED from the farm device pool.")
        
        if not available_devices:
            print("❌ No devices available for farm management!")
            return None
        
        print(f"\n📱 Available devices: {', '.join(available_devices)}")
        print("\n💡 Examples of valid input:")
        print("   • emulator-5554")
        print("   • emulator-5556")
        print("   • device_serial_number")
        print("   • none (if no master device is running)")
        
        while True:
            print(f"\n🔍 Enter the master device ID to exclude:")
            print(f"   (Available: {', '.join(available_devices)}, or 'none')")
            
            user_input = input("Master device ID: ").strip()
            
            if not user_input:
                print("❌ Please enter a device ID or 'none'")
                continue
            
            if user_input.lower() == 'none':
                print("✅ No master device specified - all devices will be used as farm devices")
                return None
                
            if user_input in available_devices:
                print(f"✅ Master device '{user_input}' will be excluded from farm")
                return user_input
            else:
                print(f"❌ Invalid device ID: '{user_input}'")
                print(f"   Available devices: {', '.join(available_devices)}")
                
                # Ask if user wants to retry or exit
                retry = input("\n🔄 Try again? (y/n): ").strip().lower()
                if retry not in ['y', 'yes']:
                    print("👋 Exiting...")
                    return "EXIT"

    async def run(self, specific_devices: Optional[List[str]] = None, master_device: Optional[str] = None):
        """Main execution method"""
        logger.info("🚀 Starting Farm Device Manager...")
        print("🚀 Starting Farm Device Manager...")
        print("=" * 50)
        
        # Discover devices
        if specific_devices:
            logger.info(f"Using specific devices: {specific_devices}")
            available_devices = await self.discover_devices()
            devices_to_use = [d for d in specific_devices if d in available_devices]
            if not devices_to_use:
                logger.error("❌ None of the specified devices are available")
                return
        else:
            available_devices = await self.discover_devices()
            devices_to_use = available_devices.copy()
        
        if not devices_to_use:
            logger.error("❌ No devices found. Please connect at least one Android device.")
            return
        
        # Prompt for master device if not specified
        if master_device is None:
            master_device = self.prompt_for_master_device(devices_to_use)
            if master_device == "EXIT":
                return
        
        # Always try to identify the master device if not specified
        if not master_device:
            # Try to detect master device by checking running processes
            try:
                logger.info("Attempting to auto-detect master device...")
                process = await asyncio.create_subprocess_exec(
                    'ps', 'aux',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                output = stdout.decode('utf-8')
                
                # Check if master-recorder.py is running with a device ID
                for line in output.split('\n'):
                    if 'master-recorder.py' in line and any(device in line for device in available_devices):
                        for device in available_devices:
                            if device in line:
                                master_device = device
                                logger.info(f"🔍 Auto-detected master device: {master_device}")
                                print(f"🔍 Auto-detected master device: {master_device}")
                                break
                        if master_device:
                            break
            except Exception as e:
                logger.error(f"Error auto-detecting master device: {e}")
        
        # Store master device ID for use in monitor_device_health
        self.master_device = master_device

        # Exclude master device from farm devices
        if master_device and master_device in devices_to_use:
            devices_to_use.remove(master_device)
            logger.info(f"🚫 Excluded master device from farm: {master_device}")
            print(f"🚫 Excluded master device from farm: {master_device}")
            
            # Get master device model for better logging
            try:
                master_model_process = await asyncio.create_subprocess_exec(
                    'adb', '-s', master_device, 'shell', 'getprop', 'ro.product.model',
                    stdout=asyncio.subprocess.PIPE
                )
                master_model_stdout, _ = await master_model_process.communicate()
                master_model = master_model_stdout.decode('utf-8').strip() or "Unknown"
                print(f"ℹ️ Master device: {master_device} ({master_model})")
            except Exception as e:
                logger.error(f"Error getting master device model: {e}")
        
        if not devices_to_use:
            logger.error("❌ No farm devices available after excluding master device.")
            print("❌ No farm devices available after excluding master device.")
            print("   Please ensure you have multiple devices connected.")
            return
        
        # Initialize device info and start connection handlers only for farm devices
        farm_device_tasks = []
        for device_id in devices_to_use:
            device_info = await self.get_device_info(device_id)
            if device_info:
                self.devices[device_id] = device_info
                task = asyncio.create_task(self.handle_device_connection(device_info))
                farm_device_tasks.append(task)
        
        if not self.devices:
            logger.error("❌ Failed to initialize any devices")
            return
        
        logger.info(f"🎯 Managing {len(self.devices)} farm device(s)")
        print(f"🎯 Managing {len(self.devices)} farm device(s)")
        
        # Start tasks
        tasks = []
        tasks.extend(farm_device_tasks) # Add farm device connection tasks
        
        # Start monitoring tasks
        tasks.append(asyncio.create_task(self.monitor_device_health()))
        tasks.append(asyncio.create_task(self.print_status()))
        
        try:
            # Wait for all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down farm device manager...")
            print("🛑 Shutting down farm device manager...")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Farm Device Executor - Manages multiple Android devices in a farm')
    parser.add_argument('devices', nargs='*', help='Specific device IDs to use (optional)')
    parser.add_argument('--server', default='ws://127.0.0.1:8765/farm', help='Central server URL')
    parser.add_argument('--master', help='Master device ID to exclude from farm (optional)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose logging')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Log level')

    args = parser.parse_args()

    # Set log level based on debug flag or explicit log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    print("🚀 Farm Device Executor")
    print("=" * 30)
    print("This script manages connected Android devices as farm devices.")
    print("It will discover devices and exclude the master device from the farm pool.")
    print("")
    
    if args.devices:
        print(f"🎯 Target devices: {args.devices}")
    else:
        print("🔍 Auto-discovering all connected devices...")
    
    if args.master:
        print(f"🚫 Master device to exclude: {args.master}")
    else:
        print("❓ Master device will be prompted during execution")
    
    print(f"🌐 Central server: {args.server}")
    print("")
    
    # Create and run farm manager
    farm_manager = FarmDeviceManager(args.server, debug=args.debug)

    try:
        asyncio.run(farm_manager.run(
            specific_devices=args.devices if args.devices else None,
            master_device=args.master
        ))
    except KeyboardInterrupt:
        print("\n🛑 Farm Device Executor stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Farm Device Executor crashed: {e}")
        logger.critical(f"Farm Device Executor crashed: {e}")

if __name__ == "__main__":
    main()