#!/usr/bin/env python3
"""
Script to install and setup uiautomator2 for enhanced Android automation.
This provides more reliable tap execution compared to basic ADB commands.
"""

import subprocess
import sys
import os

def run_command(cmd, description=""):
    """Run a command and return success status"""
    print(f"🔧 {description}")
    print(f"   Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required for uiautomator2")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_uiautomator2():
    """Install uiautomator2 package"""
    print("\n📦 Installing uiautomator2...")
    return run_command([sys.executable, "-m", "pip", "install", "uiautomator2>=3.0.0"], 
                      "Installing uiautomator2 Python package")

def check_adb():
    """Check if ADB is available"""
    print("\n🔍 Checking ADB availability...")
    return run_command(["adb", "version"], "Checking ADB version")

def setup_uiautomator2_on_devices():
    """Setup uiautomator2 on connected devices"""
    print("\n📱 Setting up uiautomator2 on connected devices...")
    
    # Get connected devices
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        devices = []
        for line in lines:
            if line.strip() and '\tdevice' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        
        if not devices:
            print("   ⚠️ No devices found. Please connect an Android device and enable USB debugging.")
            return False
        
        print(f"   Found {len(devices)} device(s): {', '.join(devices)}")
        
        # Setup uiautomator2 on each device
        success_count = 0
        for device_id in devices:
            print(f"\n   📱 Setting up {device_id}...")
            if run_command([sys.executable, "-m", "uiautomator2", "init", "--serial", device_id], 
                          f"Initializing uiautomator2 on {device_id}"):
                success_count += 1
            else:
                print(f"   ⚠️ Failed to setup uiautomator2 on {device_id}")
        
        print(f"\n   ✅ Successfully setup uiautomator2 on {success_count}/{len(devices)} devices")
        return success_count > 0
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to get device list: {e}")
        return False

def test_uiautomator2():
    """Test uiautomator2 installation"""
    print("\n🧪 Testing uiautomator2 installation...")
    
    try:
        import uiautomator2 as u2
        print("   ✅ uiautomator2 import successful")
        
        # Try to connect to a device
        try:
            d = u2.connect()
            info = d.info
            print(f"   ✅ Connected to device: {info.get('productName', 'Unknown')}")
            print(f"   📱 Screen: {info.get('displayWidth', '?')}x{info.get('displayHeight', '?')}")
            return True
        except Exception as e:
            print(f"   ⚠️ Could not connect to device: {e}")
            print("   💡 This is normal if no device is connected or uiautomator2 server is not running")
            return True  # Installation is still successful
            
    except ImportError as e:
        print(f"   ❌ Failed to import uiautomator2: {e}")
        return False

def main():
    """Main installation process"""
    print("🚀 UIAutomator2 Installation and Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check ADB
    if not check_adb():
        print("❌ ADB is required but not found. Please install Android SDK Platform Tools.")
        return False
    
    # Install uiautomator2
    if not install_uiautomator2():
        print("❌ Failed to install uiautomator2")
        return False
    
    # Test installation
    if not test_uiautomator2():
        print("❌ uiautomator2 installation test failed")
        return False
    
    # Setup on devices (optional)
    print("\n🤖 Would you like to setup uiautomator2 on connected devices now?")
    print("   This will install the uiautomator2 server APK on your devices.")
    response = input("   Setup on devices? (y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        setup_uiautomator2_on_devices()
    else:
        print("   ⏭️ Skipping device setup. You can run this later with:")
        print("      python -m uiautomator2 init")
    
    print("\n🎉 UIAutomator2 installation completed!")
    print("\n💡 Usage tips:")
    print("   • The farm device executor will now try uiautomator2 for more reliable taps")
    print("   • If uiautomator2 fails, it will fallback to standard ADB commands")
    print("   • For manual testing: python -c \"import uiautomator2 as u2; d = u2.connect(); d.click(100, 100)\"")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
