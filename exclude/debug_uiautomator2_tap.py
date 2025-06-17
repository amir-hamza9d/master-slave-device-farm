#!/usr/bin/env python3
"""
Debug script to test UIAutomator2 tap functionality
This helps identify why UIAutomator2 taps appear successful but don't work
"""

import sys
import time
import subprocess
import asyncio

def run_adb_command(cmd):
    """Run ADB command and return result"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def get_devices():
    """Get list of connected devices"""
    returncode, stdout, stderr = run_adb_command(['adb', 'devices'])
    if returncode != 0:
        print(f"❌ Failed to get devices: {stderr}")
        return []
    
    devices = []
    for line in stdout.split('\n')[1:]:  # Skip header
        if 'device' in line and line.strip():
            device_id = line.split()[0]
            devices.append(device_id)
    return devices

def test_uiautomator2_basic(device_id):
    """Test basic UIAutomator2 functionality"""
    print(f"\n🧪 Testing UIAutomator2 basic functionality on {device_id}")
    
    try:
        import uiautomator2 as u2
        print("   ✅ UIAutomator2 import successful")
        
        # Connect to device
        d = u2.connect(device_id)
        print(f"   ✅ Connected to {device_id}")
        
        # Get device info
        info = d.info
        print(f"   📱 Device: {info.get('productName', 'Unknown')}")
        print(f"   📏 Screen: {info.get('displayWidth', '?')}x{info.get('displayHeight', '?')}")
        
        # Test if device is responsive
        current_app = d.app_current()
        print(f"   📱 Current app: {current_app.get('package', 'Unknown')}")
        
        # Test screenshot capability
        try:
            screenshot = d.screenshot()
            print(f"   📸 Screenshot: {screenshot.size if screenshot else 'Failed'}")
        except Exception as e:
            print(f"   ⚠️ Screenshot failed: {e}")
        
        return True, d
        
    except ImportError:
        print("   ❌ UIAutomator2 not installed")
        return False, None
    except Exception as e:
        print(f"   ❌ UIAutomator2 error: {e}")
        return False, None

def test_tap_methods(device_id, x=100, y=200):
    """Test different tap methods"""
    print(f"\n🎯 Testing tap methods on {device_id} at ({x}, {y})")
    
    # Test 1: Standard ADB input tap
    print("\n1️⃣ Testing ADB input tap...")
    cmd = ['adb', '-s', device_id, 'shell', 'input', 'tap', str(x), str(y)]
    returncode, stdout, stderr = run_adb_command(cmd)
    if returncode == 0:
        print("   ✅ ADB input tap executed successfully")
    else:
        print(f"   ❌ ADB input tap failed: {stderr}")
    
    # Test 2: UIAutomator2 tap
    print("\n2️⃣ Testing UIAutomator2 tap...")
    success, d = test_uiautomator2_basic(device_id)
    if success and d:
        try:
            # Get current activity before tap
            pre_activity = d.app_current().get('activity', 'unknown')
            print(f"   📱 Pre-tap activity: {pre_activity}")
            
            # Execute tap
            d.click(x, y)
            print(f"   ✅ UIAutomator2 click({x}, {y}) executed")
            
            # Wait and check activity again
            time.sleep(0.5)
            post_activity = d.app_current().get('activity', 'unknown')
            print(f"   📱 Post-tap activity: {post_activity}")
            
            # Test alternative UIAutomator2 method
            print("   🔄 Testing UIAutomator2 shell method...")
            d.shell(f"input tap {x} {y}")
            print(f"   ✅ UIAutomator2 shell tap executed")
            
        except Exception as e:
            print(f"   ❌ UIAutomator2 tap failed: {e}")
    
    # Test 3: Touchscreen swipe
    print("\n3️⃣ Testing touchscreen swipe...")
    cmd = ['adb', '-s', device_id, 'shell', 'input', 'touchscreen', 'swipe', str(x), str(y), str(x), str(y), '100']
    returncode, stdout, stderr = run_adb_command(cmd)
    if returncode == 0:
        print("   ✅ Touchscreen swipe executed successfully")
    else:
        print(f"   ❌ Touchscreen swipe failed: {stderr}")

def check_uiautomator2_server(device_id):
    """Check UIAutomator2 server status"""
    print(f"\n🔍 Checking UIAutomator2 server status on {device_id}")
    
    # Check if UIAutomator2 server is running
    cmd = ['adb', '-s', device_id, 'shell', 'ps', '|', 'grep', 'uiautomator']
    returncode, stdout, stderr = run_adb_command(cmd)
    if stdout:
        print(f"   ✅ UIAutomator2 processes found:\n{stdout}")
    else:
        print("   ⚠️ No UIAutomator2 processes found")
    
    # Check UIAutomator2 service
    try:
        import uiautomator2 as u2
        d = u2.connect(device_id)
        
        # Try to get service info
        try:
            service_info = d.service("uiautomator").running()
            print(f"   📊 UIAutomator2 service running: {service_info}")
        except:
            print("   ⚠️ Cannot get UIAutomator2 service status")
            
        # Check if we can perform basic operations
        try:
            d.info
            print("   ✅ UIAutomator2 basic operations working")
        except Exception as e:
            print(f"   ❌ UIAutomator2 basic operations failed: {e}")
            
    except Exception as e:
        print(f"   ❌ UIAutomator2 server check failed: {e}")

def main():
    """Main debug function"""
    print("🔧 UIAutomator2 Tap Debug Tool")
    print("=" * 50)
    
    # Get devices
    devices = get_devices()
    if not devices:
        print("❌ No devices found")
        return
    
    print(f"📱 Found devices: {devices}")
    
    # Select device
    if len(devices) == 1:
        device_id = devices[0]
        print(f"🎯 Using device: {device_id}")
    else:
        print("\nSelect device:")
        for i, device in enumerate(devices):
            print(f"  {i+1}. {device}")

        while True:
            user_input = input("Enter choice (number or device name): ").strip()

            # Try as number first
            try:
                choice = int(user_input) - 1
                if 0 <= choice < len(devices):
                    device_id = devices[choice]
                    break
                else:
                    print(f"❌ Invalid number. Please enter 1-{len(devices)}")
                    continue
            except ValueError:
                pass

            # Try as device name
            if user_input in devices:
                device_id = user_input
                break

            print(f"❌ Invalid choice '{user_input}'. Please enter a number (1-{len(devices)}) or device name")
            print(f"Available devices: {', '.join(devices)}")
    
    # Get screen resolution
    cmd = ['adb', '-s', device_id, 'shell', 'wm', 'size']
    returncode, stdout, stderr = run_adb_command(cmd)
    if returncode == 0 and 'Physical size:' in stdout:
        resolution = stdout.split('Physical size:')[1].strip()
        width, height = map(int, resolution.split('x'))
        print(f"📏 Screen resolution: {width}x{height}")
        
        # Use center of screen for testing
        test_x = width // 2
        test_y = height // 2
    else:
        print("⚠️ Could not get screen resolution, using default coordinates")
        test_x, test_y = 540, 960
    
    print(f"🎯 Test coordinates: ({test_x}, {test_y})")
    
    # Run tests
    check_uiautomator2_server(device_id)
    test_tap_methods(device_id, test_x, test_y)
    
    print(f"\n💡 Recommendations:")
    print(f"   • If ADB input tap works but UIAutomator2 doesn't, there may be a UIAutomator2 server issue")
    print(f"   • Try: python -m uiautomator2 init --serial {device_id}")
    print(f"   • Or restart the device and try again")
    print(f"   • Check if the device screen is unlocked and responsive")

if __name__ == "__main__":
    main()
