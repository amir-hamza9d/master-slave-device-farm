#!/usr/bin/env python3
"""
Setup UIAutomator2 for Farm Device Synchronization System
This script installs and configures UIAutomator2 for enhanced tap reliability on slave devices.
"""

import subprocess
import sys
import asyncio
import json
from typing import List, Dict

def run_command(cmd: List[str], description: str = "") -> tuple:
    """Run a command and return (success, stdout, stderr)"""
    print(f"🔧 {description}")
    print(f"   Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   ✅ {result.stdout.strip()}")
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        return False, e.stdout if e.stdout else "", e.stderr if e.stderr else ""

def check_python_version() -> bool:
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required for UIAutomator2")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_uiautomator2() -> bool:
    """Install UIAutomator2 package"""
    print("\n📦 Installing UIAutomator2...")
    success, stdout, stderr = run_command(
        [sys.executable, "-m", "pip", "install", "uiautomator2>=3.0.0"], 
        "Installing UIAutomator2 Python package"
    )
    return success

def get_connected_devices() -> List[str]:
    """Get list of connected Android devices"""
    print("\n📱 Discovering connected devices...")
    success, stdout, stderr = run_command(["adb", "devices"], "Getting device list")
    
    if not success:
        return []
    
    devices = []
    lines = stdout.strip().split('\n')[1:]  # Skip header
    for line in lines:
        if line.strip() and '\tdevice' in line:
            device_id = line.split('\t')[0]
            devices.append(device_id)
    
    print(f"   Found {len(devices)} device(s): {', '.join(devices)}")
    return devices

def get_device_info(device_id: str) -> Dict:
    """Get device information"""
    info = {"device_id": device_id}
    
    # Get model
    success, stdout, stderr = run_command(
        ['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
        f"Getting model for {device_id}"
    )
    info["model"] = stdout.strip() if success else "Unknown"
    
    # Get Android version
    success, stdout, stderr = run_command(
        ['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'],
        f"Getting Android version for {device_id}"
    )
    info["android_version"] = stdout.strip() if success else "Unknown"
    
    # Get screen resolution
    success, stdout, stderr = run_command(
        ['adb', '-s', device_id, 'shell', 'wm', 'size'],
        f"Getting screen resolution for {device_id}"
    )
    if success and 'Physical size:' in stdout:
        resolution = stdout.split(': ')[1].split('\n')[0]
        info["resolution"] = resolution
    else:
        info["resolution"] = "Unknown"
    
    return info

def setup_uiautomator2_on_device(device_id: str) -> bool:
    """Setup UIAutomator2 on a specific device"""
    print(f"\n🤖 Setting up UIAutomator2 on {device_id}...")
    
    # Initialize UIAutomator2 on device
    success, stdout, stderr = run_command(
        [sys.executable, "-m", "uiautomator2", "init", "--serial", device_id],
        f"Initializing UIAutomator2 on {device_id}"
    )
    
    if not success:
        print(f"   ⚠️ UIAutomator2 init failed for {device_id}")
        return False
    
    # Test UIAutomator2 connection
    try:
        import uiautomator2 as u2
        d = u2.connect(device_id)
        device_info = d.info
        print(f"   ✅ UIAutomator2 test successful: {device_info.get('productName', 'Unknown')}")
        print(f"   📱 Screen: {device_info.get('displayWidth', '?')}x{device_info.get('displayHeight', '?')}")
        return True
    except Exception as e:
        print(f"   ❌ UIAutomator2 test failed: {e}")
        return False

def test_tap_functionality(device_id: str) -> bool:
    """Test UIAutomator2 tap functionality"""
    print(f"\n🧪 Testing UIAutomator2 tap on {device_id}...")
    
    try:
        import uiautomator2 as u2
        d = u2.connect(device_id)
        
        # Get screen info
        info = d.info
        width = info.get('displayWidth', 1080)
        height = info.get('displayHeight', 1920)
        
        # Test tap at center of screen
        center_x = width // 2
        center_y = height // 2
        
        print(f"   🎯 Testing tap at center ({center_x}, {center_y})")
        d.click(center_x, center_y)
        
        print(f"   ✅ UIAutomator2 tap test successful on {device_id}")
        return True
        
    except Exception as e:
        print(f"   ❌ UIAutomator2 tap test failed on {device_id}: {e}")
        return False

def main():
    """Main setup process"""
    print("🤖 UIAutomator2 Farm Device Setup")
    print("=" * 50)
    print("This script will install and configure UIAutomator2 for enhanced")
    print("tap reliability on your farm devices (slave devices).")
    print("")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check ADB
    print("\n🔍 Checking ADB availability...")
    success, stdout, stderr = run_command(["adb", "version"], "Checking ADB version")
    if not success:
        print("❌ ADB is required but not found. Please install Android SDK Platform Tools.")
        return False
    
    # Install UIAutomator2
    if not install_uiautomator2():
        print("❌ Failed to install UIAutomator2")
        return False
    
    # Get connected devices
    devices = get_connected_devices()
    if not devices:
        print("❌ No devices found. Please connect Android devices and enable USB debugging.")
        return False
    
    # Get device information
    print("\n📋 Device Information:")
    print("-" * 40)
    device_infos = {}
    for device_id in devices:
        info = get_device_info(device_id)
        device_infos[device_id] = info
        print(f"📱 {device_id}: {info['model']} (Android {info['android_version']}, {info['resolution']})")
    
    # Ask which devices to setup
    print(f"\n🤖 Setup UIAutomator2 on which devices?")
    print("   (Typically you want to setup on slave/farm devices, not the master)")
    print("   Enter device numbers separated by spaces, or 'all' for all devices:")
    
    for i, device_id in enumerate(devices):
        info = device_infos[device_id]
        print(f"   {i+1}. {device_id} ({info['model']})")
    
    choice = input("\n   Your choice: ").strip().lower()
    
    if choice == 'all':
        devices_to_setup = devices
    else:
        try:
            indices = [int(x) - 1 for x in choice.split()]
            devices_to_setup = [devices[i] for i in indices if 0 <= i < len(devices)]
        except (ValueError, IndexError):
            print("❌ Invalid choice. Exiting.")
            return False
    
    if not devices_to_setup:
        print("❌ No devices selected. Exiting.")
        return False
    
    print(f"\n🎯 Setting up UIAutomator2 on {len(devices_to_setup)} device(s)...")
    
    # Setup UIAutomator2 on selected devices
    success_count = 0
    for device_id in devices_to_setup:
        if setup_uiautomator2_on_device(device_id):
            success_count += 1
    
    print(f"\n📊 Setup Results:")
    print(f"   ✅ Successful: {success_count}/{len(devices_to_setup)} devices")
    
    if success_count > 0:
        print(f"\n🧪 Testing tap functionality...")
        test_success_count = 0
        for device_id in devices_to_setup:
            if test_tap_functionality(device_id):
                test_success_count += 1
        
        print(f"\n📊 Tap Test Results:")
        print(f"   ✅ Working: {test_success_count}/{success_count} devices")
    
    # Final summary
    print(f"\n🎉 UIAutomator2 Farm Setup Complete!")
    print(f"   📱 Devices configured: {success_count}")
    print(f"   🎯 Tap tests passed: {test_success_count if success_count > 0 else 0}")
    
    if success_count > 0:
        print(f"\n💡 Next Steps:")
        print(f"   1. Run your farm device executor: python src/farm_device_executor.py")
        print(f"   2. UIAutomator2 will be used as the primary tap method")
        print(f"   3. Look for '🤖 UIAutomator2 TAP SUCCESS' in the logs")
        print(f"   4. Enjoy improved tap reliability! 🚀")
    else:
        print(f"\n⚠️ Setup failed. Please check:")
        print(f"   • Devices are connected and USB debugging is enabled")
        print(f"   • ADB can communicate with devices")
        print(f"   • Devices are unlocked and responsive")
    
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
