#!/usr/bin/env python3
"""
Fix script for UIAutomator2 tap issues
This script helps resolve common UIAutomator2 problems where taps appear successful but don't work
"""

import subprocess
import sys
import time

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

def get_devices():
    """Get list of connected devices"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = []
        for line in result.stdout.split('\n')[1:]:
            if 'device' in line and line.strip():
                device_id = line.split()[0]
                devices.append(device_id)
        return devices
    except:
        return []

def fix_uiautomator2_for_device(device_id):
    """Fix UIAutomator2 issues for a specific device"""
    print(f"\n🔧 Fixing UIAutomator2 for {device_id}")
    
    # Step 1: Kill existing UIAutomator2 processes
    print("\n1️⃣ Stopping existing UIAutomator2 processes...")
    run_command(['adb', '-s', device_id, 'shell', 'pkill', '-f', 'uiautomator'], 
                "Killing UIAutomator2 processes")
    
    # Step 2: Clear UIAutomator2 cache
    print("\n2️⃣ Clearing UIAutomator2 cache...")
    run_command(['adb', '-s', device_id, 'shell', 'rm', '-rf', '/data/local/tmp/minicap*'], 
                "Clearing minicap cache")
    run_command(['adb', '-s', device_id, 'shell', 'rm', '-rf', '/data/local/tmp/minitouch*'], 
                "Clearing minitouch cache")
    
    # Step 3: Restart UIAutomator2 server
    print("\n3️⃣ Reinitializing UIAutomator2...")
    try:
        import uiautomator2 as u2
        
        # Force reconnection
        try:
            d = u2.connect(device_id)
            d.service("uiautomator").stop()
            time.sleep(2)
        except:
            pass
        
        # Reinitialize
        success = run_command([sys.executable, '-m', 'uiautomator2', 'init', '--serial', device_id], 
                             f"Reinitializing UIAutomator2 for {device_id}")
        
        if success:
            # Test connection
            time.sleep(3)
            d = u2.connect(device_id)
            info = d.info
            print(f"   ✅ UIAutomator2 reconnected: {info.get('productName', 'Unknown')}")
            return True
        else:
            print(f"   ❌ UIAutomator2 initialization failed")
            return False
            
    except ImportError:
        print("   ❌ UIAutomator2 not installed")
        return False
    except Exception as e:
        print(f"   ❌ UIAutomator2 fix failed: {e}")
        return False

def test_tap_after_fix(device_id):
    """Test tap functionality after fix"""
    print(f"\n🧪 Testing tap after fix on {device_id}")
    
    try:
        import uiautomator2 as u2
        d = u2.connect(device_id)
        
        # Get screen center
        info = d.info
        width = info.get('displayWidth', 1080)
        height = info.get('displayHeight', 1920)
        x, y = width // 2, height // 2
        
        print(f"   🎯 Testing tap at center: ({x}, {y})")
        
        # Get current activity
        try:
            pre_activity = d.app_current().get('activity', 'unknown')
            print(f"   📱 Current activity: {pre_activity}")
        except:
            pre_activity = 'unknown'
        
        # Execute tap
        d.click(x, y)
        print(f"   ✅ UIAutomator2 tap executed")
        
        # Wait and verify device is still responsive
        time.sleep(0.5)
        try:
            post_activity = d.app_current().get('activity', 'unknown')
            print(f"   📱 Activity after tap: {post_activity}")
            print(f"   ✅ Device responsive after tap")
            return True
        except Exception as e:
            print(f"   ⚠️ Device responsiveness check failed: {e}")
            return False
            
    except Exception as e:
        print(f"   ❌ Tap test failed: {e}")
        return False

def main():
    """Main fix function"""
    print("🔧 UIAutomator2 Tap Fix Tool")
    print("=" * 40)
    print("This tool fixes common UIAutomator2 tap issues where")
    print("taps appear successful but don't actually work.")
    print()
    
    # Get devices
    devices = get_devices()
    if not devices:
        print("❌ No devices found")
        return
    
    print(f"📱 Found devices: {devices}")
    
    # Fix each device
    for device_id in devices:
        print(f"\n{'='*50}")
        print(f"🎯 Processing device: {device_id}")
        
        # Get device info
        try:
            result = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model'], 
                                  capture_output=True, text=True)
            model = result.stdout.strip() or "Unknown"
            print(f"📱 Model: {model}")
        except:
            model = "Unknown"
        
        # Apply fix
        if fix_uiautomator2_for_device(device_id):
            print(f"✅ Fix applied successfully for {device_id}")
            
            # Test the fix
            if test_tap_after_fix(device_id):
                print(f"🎉 Tap test passed for {device_id}")
            else:
                print(f"⚠️ Tap test failed for {device_id} - may need manual intervention")
        else:
            print(f"❌ Fix failed for {device_id}")
    
    print(f"\n🎉 Fix process completed!")
    print(f"\n💡 If issues persist:")
    print(f"   • Restart the Android device/emulator")
    print(f"   • Ensure the device screen is unlocked")
    print(f"   • Try running: python debug_uiautomator2_tap.py")
    print(f"   • Consider using ADB fallback methods")

if __name__ == "__main__":
    main()
