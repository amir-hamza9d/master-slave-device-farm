import subprocess
import re
import json
import asyncio
import websockets
import logging
import time
import argparse
from typing import Dict, List, Optional, Tuple

# Parse command line arguments
parser = argparse.ArgumentParser(description='Master Recorder for device synchronization')
parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose logging')
args = parser.parse_args()

# Set logging level based on debug flag
log_level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("MasterRecorder")

# --- WebSocket Configuration ---
# IMPORTANT: This should be the IP address of your Central Server.
# For an Android emulator on the same PC, "127.0.0.1" (localhost) is correct.
CENTRAL_SERVER_URL = "ws://127.0.0.1:8765/master"

# --- ADB Event Parsing Regex ---
# Updated regex to handle different getevent output formats
EVENT_LINE_REGEX = re.compile(r'(?:\[\s*\d+\.\d+\]\s*)?(/dev/input/event\d+):\s*(\w+)\s*(\w+)\s*([0-9a-fA-F]+)') # Made timestamp optional

current_touch_event = {"x": None, "y": None, "down": False}

async def connect_websocket():
    while True:
        try:
            websocket = await websockets.connect(CENTRAL_SERVER_URL)
            logger.info(f"Connected to Central Server: {CENTRAL_SERVER_URL}")
            return websocket
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def send_action(websocket, action_data):
    if websocket:
        try:
            await websocket.send(json.dumps(action_data))
            action_desc = action_data['action']
            if 'x' in action_data and 'y' in action_data:
                action_desc += f" at ({action_data['x']}, {action_data['y']})"
            elif 'key_code' in action_data:
                action_desc += f" key {action_data['key_code']}"
            logger.info(f"Sent action: {action_desc}")
            print(f"📤 SENT TO CENTRAL SERVER: {action_desc}")
        except websockets.exceptions.ConnectionClosedOK:
            logger.warning("WebSocket closed. Reconnecting...")
            return False
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed. Reconnecting...")
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    else:
        logger.warning("WebSocket not connected. Cannot send message.")
        return False
    return True

async def get_available_devices():
    """Get list of all available devices"""
    try:
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
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    device_id = parts[0]
                    devices.append(device_id)
        
        return devices
    except Exception as e:
        logger.error(f"Error getting available devices: {e}")
        return []

async def prompt_for_master_device():
    """Prompt user to select master device with validation"""
    print("\n" + "="*60)
    print("🎯 MASTER DEVICE SELECTION")
    print("="*60)
    
    # Get available devices
    available_devices = await get_available_devices()
    
    if not available_devices:
        print("❌ No Android devices found!")
        print("   Please ensure:")
        print("   • Android emulators are running")
        print("   • Physical devices are connected and authorized")
        print("   • ADB is properly installed and in PATH")
        return None
    
    print(f"📱 Found {len(available_devices)} available device(s):")
    for i, device in enumerate(available_devices, 1):
        print(f"   {i}. {device}")
    
    print("\n💡 Examples of valid input:")
    print("   • emulator-5554")
    print("   • emulator-5556")
    print("   • device_serial_number")
    
    while True:
        print(f"\n🔍 Please enter the master device ID:")
        print(f"   (Choose from: {', '.join(available_devices)})")
        
        user_input = input("Master device ID: ").strip()
        
        if not user_input:
            print("❌ Please enter a device ID")
            continue
            
        if user_input in available_devices:
            print(f"✅ Selected master device: {user_input}")
            return user_input
        else:
            print(f"❌ Invalid device ID: '{user_input}'")
            print(f"   Available devices: {', '.join(available_devices)}")
            
            # Ask if user wants to retry or exit
            retry = input("\n🔄 Try again? (y/n): ").strip().lower()
            if retry not in ['y', 'yes']:
                print("👋 Exiting...")
                return None

async def validate_device_connection(device_id):
    """Validate that the device is accessible via ADB"""
    try:
        logger.info(f"🔍 Validating connection to device: {device_id}")
        
        # Test basic ADB connection
        process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'echo', 'connection_test',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"❌ Cannot connect to device {device_id}: {stderr.decode('utf-8')}")
            return False
            
        logger.info(f"✅ Device {device_id} is accessible")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validating device {device_id}: {e}")
        return False

async def get_screen_resolution(device_id: str) -> Dict[str, int]:
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

async def get_device_info(device_id):
    """Get device information for debugging"""
    try:
        # Get device model
        model_process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model',
            stdout=asyncio.subprocess.PIPE
        )
        model_stdout, _ = await model_process.communicate()
        model = model_stdout.decode('utf-8').strip()
        
        # Get Android version
        version_process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release',
            stdout=asyncio.subprocess.PIPE
        )
        version_stdout, _ = await version_process.communicate()
        version = version_stdout.decode('utf-8').strip()
        
        # Get screen resolution
        resolution = await get_screen_resolution(device_id)

        return {
            "id": device_id,
            "model": model,
            "android_version": version,
            "screen_width": resolution["width"],
            "screen_height": resolution["height"]
        }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {"id": device_id, "model": "Unknown", "android_version": "Unknown", "screen_width": 0, "screen_height": 0}

async def get_input_device_capabilities(device_id: str, event_path: str) -> Dict[str, int]:
    """Get input device capabilities (e.g., max X/Y values)"""
    capabilities = {"ABS_MT_POSITION_X_MAX": 0, "ABS_MT_POSITION_Y_MAX": 0}
    try:
        logger.info(f"🔍 Getting capabilities for {event_path} on {device_id}")
        process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getevent', '-p', event_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        output = stdout.decode('utf-8').strip()
        logger.debug(f"Raw getevent -p output for {event_path}:\n{output}")

        # More flexible regex to find max values for ABS_MT_POSITION_X/Y or ABS_X/Y
        # It looks for 'ABS_MT_POSITION_X', 'ABS_X', 'ABS_MT_POSITION_Y', 'ABS_Y'
        # and captures the 'max' value.
        x_max_match = re.search(r'(?:ABS_MT_POSITION_X|ABS_X|0035)\s*:\s*.*?\s*max\s*(\d+)', output)
        y_max_match = re.search(r'(?:ABS_MT_POSITION_Y|ABS_Y|0036)\s*:\s*.*?\s*max\s*(\d+)', output)

        if x_max_match:
            capabilities["ABS_MT_POSITION_X_MAX"] = int(x_max_match.group(1))
            logger.debug(f"Found ABS_MT_POSITION_X_MAX: {capabilities['ABS_MT_POSITION_X_MAX']}")
        else:
            logger.warning(f"Could not find ABS_MT_POSITION_X or ABS_X max for {event_path}.")
        
        if y_max_match:
            capabilities["ABS_MT_POSITION_Y_MAX"] = int(y_max_match.group(1))
            logger.debug(f"Found ABS_MT_POSITION_Y_MAX: {capabilities['ABS_MT_POSITION_Y_MAX']}")
        else:
            logger.warning(f"Could not find ABS_MT_POSITION_Y or ABS_Y max for {event_path}.")
            
        if capabilities["ABS_MT_POSITION_X_MAX"] == 0 or capabilities["ABS_MT_POSITION_Y_MAX"] == 0:
            logger.warning(f"Final max X/Y capabilities are zero for {event_path}. Falling back to defaults.")
            # Fallback to common large values if not found, to prevent division by zero or tiny scaling
            if capabilities["ABS_MT_POSITION_X_MAX"] == 0: capabilities["ABS_MT_POSITION_X_MAX"] = 4095
            if capabilities["ABS_MT_POSITION_Y_MAX"] == 0: capabilities["ABS_MT_POSITION_Y_MAX"] = 4095

        return capabilities

    except Exception as e:
        logger.error(f"Error getting input device capabilities for {event_path} on {device_id}: {e}")
        return {"ABS_MT_POSITION_X_MAX": 4095, "ABS_MT_POSITION_Y_MAX": 4095} # Default fallback

async def monitor_adb_events(websocket, device_id):
    global current_touch_event

    logger.info(f"Starting ADB shell getevent monitor for device: {device_id}")
    
    try:
        # Validate device connection
        if not await validate_device_connection(device_id):
            logger.error(f"❌ Cannot establish connection to device: {device_id}")
            return
        
        # Get and log device information
        device_info = await get_device_info(device_id)
        logger.info(f"Master device: {device_info['model']} (Android {device_info['android_version']}, ID: {device_info['id']})")
        
        # Send device info to central server for debugging
        await send_action(websocket, {
            "action": "device_info",
            "role": "master",
            "device_info": device_info
        })
        
        # Give central server and farm devices a moment to process master info
        await asyncio.sleep(2)
            
        logger.info(f"Using device: {device_id}")
        
        # Check if we can run a simple ADB command first
        test_process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'echo', 'ADB connection test', # Added -s device_id
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await test_process.communicate()
        
        if test_process.returncode != 0:
            logger.error(f"ADB test failed: {stderr.decode('utf-8')}")
            return
            
        logger.info("ADB connection test successful")
        
        # Test if getevent works at all
        logger.info("Testing getevent availability...")
        test_getevent = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getevent', '--help', # Added -s device_id
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        test_stdout, test_stderr = await test_getevent.communicate()
        print(f"🧪 GETEVENT TEST - Return code: {test_getevent.returncode}")
        if test_stdout:
            print(f"🧪 GETEVENT STDOUT: {test_stdout.decode('utf-8')[:200]}...")
        if test_stderr:
            print(f"🧪 GETEVENT STDERR: {test_stderr.decode('utf-8')[:200]}...")
        
        # Now try to run getevent
        logger.info("Starting getevent monitor...")
        print(f"🚀 Executing: adb -s {device_id} shell getevent") # Removed -t option
        process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getevent', # Removed -t option
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print(f"📋 Process started with PID: {process.pid}")
        
        # Check if stderr has any immediate errors
        print("🔍 Checking for immediate errors...")
        try:
            stderr_data = await asyncio.wait_for(process.stderr.readline(), timeout=2.0)
            if stderr_data:
                stderr_str = stderr_data.decode('utf-8')
                print(f"❌ GETEVENT ERROR: {stderr_str}")
                logger.error(f"getevent error: {stderr_str}")
                if "permission denied" in stderr_str.lower():
                    logger.error("Permission denied. Try running the script with sudo or fix ADB permissions.")
                return
            else:
                print("✅ No immediate errors from getevent")
        except asyncio.TimeoutError:
            print("✅ No immediate errors (timeout reached)")
            
        logger.info("getevent started successfully, waiting for events...")
        logger.info("Please interact with the emulator (tap, swipe, etc.) to generate events.")
        print("🔥 GETEVENT MONITOR STARTED - Tap on your emulator now!")
        
        # Skip the timeout check and go directly to event monitoring
        print("⏳ Waiting for events... (no timeout)")
        
        # Continue with the original code
        print("🔄 Starting event monitoring loop...")
        event_count = 0

        master_screen_width = device_info["screen_width"]
        master_screen_height = device_info["screen_height"]
        master_input_x_max = 0
        master_input_y_max = 0
        input_device_path_identified = False

        while True:
            line = await process.stdout.readline()
            if not line:
                print("❌ No more data from getevent process")
                logger.warning("ADB getevent stream ended or process died. Attempting to restart monitor...")
                break # Break from this loop, main() will try to reconnect
 
            event_count += 1
            line_str = line.decode('utf-8', errors='ignore').strip()
            logger.debug(f"Raw event line from adb getevent: {line_str}") # More descriptive log

            # Print raw events to console for debugging (only in debug mode)
            if args.debug:
                print(f"📱 RAW EVENT #{event_count}: {line_str}")

            match = EVENT_LINE_REGEX.match(line_str)
            if not match:
                if args.debug:
                    print(f"⚠️  Event didn't match regex pattern")
                continue

            device_path, event_type, event_code, event_value = match.groups()
            logger.debug(f"Parsed event: Device={device_path}, Type={event_type}, Code={event_code}, Value={event_value}") # Log parsed components
            if args.debug:
                print(f"🔍 PARSED: Device={device_path}, Type={event_type}, Code={event_code}, Value={event_value}")

            if not input_device_path_identified and (event_type == 'ABS' or event_type == '0003'):
                # This is the first ABS event, try to get input device capabilities
                logger.info(f"First ABS event from {device_path}. Getting input device capabilities...")
                caps = await get_input_device_capabilities(device_id, device_path)
                master_input_x_max = caps["ABS_MT_POSITION_X_MAX"]
                master_input_y_max = caps["ABS_MT_POSITION_Y_MAX"]
                input_device_path_identified = True
                logger.info(f"Master input device capabilities: X_MAX={master_input_x_max}, Y_MAX={master_input_y_max}")
                print(f"📏 MASTER INPUT CAPS: X_MAX={master_input_x_max}, Y_MAX={master_input_y_max}")

                # Send master resolution update to central server
                master_resolution_data = {
                    "action": "master_resolution_update",
                    "resolution": {
                        "width": master_screen_width,
                        "height": master_screen_height,
                        "input_x_max": master_input_x_max,
                        "input_y_max": master_input_y_max
                    }
                }
                logger.info(f"Sending master resolution update: {master_resolution_data}")
                await send_action(websocket, master_resolution_data)
 
            # Handle both hex codes (0003) and text codes (ABS)
            if event_type == 'ABS' or event_type == '0003': # Absolute events like touch positions
                # Convert hex event value to integer
                try:
                    # Try converting as hex first, then as decimal
                    event_value_int = int(event_value, 16)
                except ValueError:
                    # Fallback to decimal if hex conversion fails
                    event_value_int = int(event_value)
                
                # Handle X position (0035 = ABS_MT_POSITION_X)
                if event_code == 'ABS_MT_POSITION_X' or event_code == '0035':
                    current_touch_event["x"] = event_value_int # Store raw value
                    if args.debug:
                        print(f"👆 TOUCH X (raw): {event_value_int}")
                # Handle Y position (0036 = ABS_MT_POSITION_Y)
                elif event_code == 'ABS_MT_POSITION_Y' or event_code == '0036':
                    current_touch_event["y"] = event_value_int # Store raw value
                    if args.debug:
                        print(f"👆 TOUCH Y (raw): {event_value_int}")
                # Handle tracking ID (0039 = ABS_MT_TRACKING_ID)
                elif event_code == 'ABS_MT_TRACKING_ID' or event_code == '0039':
                    # ffffffff (4294967295) indicates finger UP (release)
                    # Any other value indicates finger DOWN (press)
                    if event_value_int == 4294967295 or event_value == 'ffffffff': # Finger UP (release)
                        if args.debug:
                            print(f"👆 FINGER UP (RELEASE)")
                        if current_touch_event["down"] and current_touch_event["x"] is not None and current_touch_event["y"] is not None:
                            action_data = {
                                "action": "tap_release",
                                "x": current_touch_event["x"],
                                "y": current_touch_event["y"],
                                "device_path": device_path
                            }
                            logger.debug(f"Preparing to send tap_release: {action_data}") # Log action data before sending
                            # Show clean action in normal mode, detailed in debug mode
                            if args.debug:
                                print(f"🚀 SENDING: tap_release at ({current_touch_event['x']}, {current_touch_event['y']}) (raw)")
                            else:
                                print(f"🎯 TAP COMPLETED")
                            await send_action(websocket, action_data)
                        current_touch_event["down"] = False
                        current_touch_event["x"] = None # Reset for next tap
                        current_touch_event["y"] = None
                    else: # Finger DOWN (press)
                        if args.debug:
                            print(f"👆 FINGER DOWN (PRESS)")
                        current_touch_event["down"] = True
                        if current_touch_event["x"] is not None and current_touch_event["y"] is not None:
                            action_data = {
                                "action": "tap_press",
                                "x": current_touch_event["x"],
                                "y": current_touch_event["y"],
                                "device_path": device_path
                            }
                            logger.debug(f"Preparing to send tap_press: {action_data}") # Log action data before sending
                            # Show clean action in normal mode, detailed in debug mode
                            if args.debug:
                                print(f"🚀 SENDING: tap_press at ({current_touch_event['x']}, {current_touch_event['y']}) (raw)")
                            else:
                                print(f"🎯 TAP STARTED")
                            await send_action(websocket, action_data)
 
            elif event_type == 'KEY' or event_type == '0001': # Key presses (for text input, back button etc.)
                key_code = event_code
                try:
                    key_value = int(event_value, 16) if event_value.startswith('0') else int(event_value)
                except ValueError:
                    key_value = int(event_value)
 
                if key_value == 1: # Key press down
                    # Show clean action in normal mode, detailed in debug mode
                    if args.debug:
                        print(f"⌨️  KEY PRESS: {key_code}")
                    else:
                        print(f"⌨️  KEY: {key_code}")
                    action_data = {"action": "key_press", "key_code": key_code, "device_path": device_path}
                    logger.debug(f"Preparing to send key_press: {action_data}") # Log action data before sending
                    await send_action(websocket, action_data)
                elif key_value == 0: # Key release
                    if args.debug:
                        print(f"⌨️  KEY RELEASE: {key_code}")
                    # Don't show key release in normal mode to avoid clutter
                    action_data = {"action": "key_release", "key_code": key_code, "device_path": device_path}
                    logger.debug(f"Preparing to send key_release: {action_data}") # Log action data before sending
                    await send_action(websocket, action_data)
 
        await process.wait() # Wait for the subprocess to finish if it somehow terminates
    except Exception as e:
        logger.error(f"Error in monitor_adb_events: {e}")
        return
 
async def main():
    # Prompt user to select master device
    master_device_id = await prompt_for_master_device()
    if not master_device_id:
        logger.error("❌ No master device selected. Exiting...")
        return
    
    print(f"\n🚀 Starting Master Recorder for device: {master_device_id}")
    print("="*60)
    
    while True: # Keep trying to connect/monitor if connection drops or adb process dies
        try:
            websocket = await connect_websocket()
            if websocket:
                await monitor_adb_events(websocket, master_device_id)
            else:
                logger.error("Could not establish initial WebSocket connection. Retrying...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        await asyncio.sleep(5) # Wait before retrying the entire connection/monitor loop

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Master Recorder stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Master Recorder crashed: {e}")
