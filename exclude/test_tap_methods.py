#!/usr/bin/env python3
"""
Test script to compare different tap execution methods.
This helps identify which method works best for your devices.
"""

import subprocess
import asyncio
import time
import sys
from typing import List, Tuple, Dict

class TapMethodTester:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.results = {}
    
    def run_adb_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run an ADB command and return return code, stdout, stderr"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def test_input_tap(self, x: int, y: int) -> bool:
        """Test standard input tap method"""
        cmd = ['adb', '-s', self.device_id, 'shell', 'input', 'tap', str(x), str(y)]
        returncode, stdout, stderr = self.run_adb_command(cmd)
        return returncode == 0
    
    def test_input_touchscreen_swipe(self, x: int, y: int) -> bool:
        """Test touchscreen swipe method (original)"""
        cmd = ['adb', '-s', self.device_id, 'shell', 'input', 'touchscreen', 'swipe', 
               str(x), str(y), str(x), str(y), '100']
        returncode, stdout, stderr = self.run_adb_command(cmd)
        return returncode == 0
    
    def test_uiautomator2(self, x: int, y: int) -> bool:
        """Test uiautomator2 method"""
        try:
            import uiautomator2 as u2
            d = u2.connect(self.device_id)
            d.click(x, y)
            return True
        except ImportError:
            print("   ⚠️ uiautomator2 not installed")
            return False
        except Exception as e:
            print(f"   ⚠️ uiautomator2 error: {e}")
            return False
    
    def test_sendevent(self, x: int, y: int) -> bool:
        """Test low-level sendevent method"""
        try:
            # Get screen resolution
            cmd = ['adb', '-s', self.device_id, 'shell', 'wm', 'size']
            returncode, stdout, stderr = self.run_adb_command(cmd)
            if returncode != 0:
                return False
            
            # Parse resolution
            size_line = stdout.split('\n')[0]
            if 'Physical size:' in size_line:
                resolution = size_line.split(': ')[1]
                width, height = map(int, resolution.split('x'))
            else:
                return False
            
            # Calculate touch coordinates
            touch_x = int((x * 32767) / width)
            touch_y = int((y * 32767) / height)
            
            # Find touch device (try common paths)
            touch_device = None
            for device_path in ['/dev/input/event2', '/dev/input/event1', '/dev/input/event0']:
                test_cmd = ['adb', '-s', self.device_id, 'shell', 'test', '-e', device_path]
                returncode, _, _ = self.run_adb_command(test_cmd)
                if returncode == 0:
                    touch_device = device_path
                    break
            
            if not touch_device:
                return False
            
            # Send touch events
            commands = [
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '3', '57', '0'],
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '3', '53', str(touch_x)],
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '3', '54', str(touch_y)],
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '0', '0', '0'],
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '3', '57', '-1'],
                ['adb', '-s', self.device_id, 'shell', 'sendevent', touch_device, '0', '0', '0'],
            ]
            
            for cmd in commands:
                returncode, _, _ = self.run_adb_command(cmd)
                if returncode != 0:
                    return False
            
            return True
            
        except Exception as e:
            print(f"   ⚠️ sendevent error: {e}")
            return False
    
    def get_device_info(self) -> Dict:
        """Get device information"""
        info = {"device_id": self.device_id}
        
        # Get model
        cmd = ['adb', '-s', self.device_id, 'shell', 'getprop', 'ro.product.model']
        returncode, stdout, stderr = self.run_adb_command(cmd)
        info["model"] = stdout if returncode == 0 else "Unknown"
        
        # Get Android version
        cmd = ['adb', '-s', self.device_id, 'shell', 'getprop', 'ro.build.version.release']
        returncode, stdout, stderr = self.run_adb_command(cmd)
        info["android_version"] = stdout if returncode == 0 else "Unknown"
        
        # Get screen resolution
        cmd = ['adb', '-s', self.device_id, 'shell', 'wm', 'size']
        returncode, stdout, stderr = self.run_adb_command(cmd)
        if returncode == 0 and 'Physical size:' in stdout:
            resolution = stdout.split(': ')[1].split('\n')[0]
            info["resolution"] = resolution
        else:
            info["resolution"] = "Unknown"
        
        return info
    
    def run_comprehensive_test(self):
        """Run comprehensive test of all tap methods"""
        print(f"\n🧪 Testing Tap Methods for {self.device_id}")
        print("=" * 60)
        
        # Get device info
        device_info = self.get_device_info()
        print(f"📱 Device: {device_info['model']} (Android {device_info['android_version']})")
        print(f"📐 Resolution: {device_info['resolution']}")
        
        # Test coordinates (center of screen and safe areas)
        if device_info['resolution'] != "Unknown":
            try:
                width, height = map(int, device_info['resolution'].split('x'))
                test_points = [
                    (width // 2, height // 2, "Center"),
                    (width // 4, height // 4, "Top-left quadrant"),
                    (3 * width // 4, 3 * height // 4, "Bottom-right quadrant"),
                    (100, 100, "Fixed point (100,100)"),
                ]
            except:
                test_points = [(100, 100, "Fixed point (100,100)")]
        else:
            test_points = [(100, 100, "Fixed point (100,100)")]
        
        # Test methods
        methods = [
            ("input_tap", self.test_input_tap, "Standard ADB input tap"),
            ("uiautomator2", self.test_uiautomator2, "UIAutomator2 click"),
            ("sendevent", self.test_sendevent, "Low-level sendevent"),
            ("touchscreen_swipe", self.test_input_touchscreen_swipe, "Touchscreen swipe (original)"),
        ]
        
        results = {}
        
        for method_name, method_func, description in methods:
            print(f"\n🔧 Testing {description}")
            method_results = []
            
            for x, y, point_desc in test_points:
                print(f"   📍 {point_desc} ({x}, {y}): ", end="")
                try:
                    success = method_func(x, y)
                    if success:
                        print("✅ Success")
                        method_results.append(True)
                    else:
                        print("❌ Failed")
                        method_results.append(False)
                except Exception as e:
                    print(f"❌ Exception: {e}")
                    method_results.append(False)
                
                # Small delay between taps
                time.sleep(0.5)
            
            success_rate = sum(method_results) / len(method_results) * 100
            results[method_name] = {
                "success_rate": success_rate,
                "description": description,
                "results": method_results
            }
            print(f"   📊 Success rate: {success_rate:.1f}%")
        
        # Summary
        print(f"\n📊 SUMMARY FOR {self.device_id}")
        print("-" * 40)
        sorted_methods = sorted(results.items(), key=lambda x: x[1]["success_rate"], reverse=True)
        
        for i, (method_name, data) in enumerate(sorted_methods):
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📍"
            print(f"{emoji} {data['description']}: {data['success_rate']:.1f}%")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS FOR {self.device_id}")
        print("-" * 40)
        best_method = sorted_methods[0]
        if best_method[1]["success_rate"] == 100:
            print(f"✅ Use {best_method[1]['description']} - 100% success rate")
        elif best_method[1]["success_rate"] >= 75:
            print(f"⚠️ Use {best_method[1]['description']} - {best_method[1]['success_rate']:.1f}% success rate")
            print("   Consider investigating why some taps fail")
        else:
            print("❌ All methods have low success rates - device may have issues")
            print("   Check if device is responsive and screen is unlocked")
        
        return results

def main():
    """Main test function"""
    print("🧪 Tap Method Comparison Test")
    print("=" * 50)
    
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
            print("❌ No devices found. Please connect an Android device and enable USB debugging.")
            return False
        
        print(f"📱 Found {len(devices)} device(s): {', '.join(devices)}")
        
        # Test each device
        all_results = {}
        for device_id in devices:
            tester = TapMethodTester(device_id)
            device_results = tester.run_comprehensive_test()
            all_results[device_id] = device_results
        
        # Overall summary
        if len(devices) > 1:
            print(f"\n🌟 OVERALL SUMMARY")
            print("=" * 50)
            for device_id, results in all_results.items():
                best_method = max(results.items(), key=lambda x: x[1]["success_rate"])
                print(f"📱 {device_id}: Best method is {best_method[1]['description']} ({best_method[1]['success_rate']:.1f}%)")
        
        print(f"\n✅ Testing completed for {len(devices)} device(s)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get device list: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
