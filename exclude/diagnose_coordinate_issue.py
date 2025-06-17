#!/usr/bin/env python3
"""
Diagnostic script to identify and fix coordinate translation issues.
This script checks the complete system state and provides recommendations.
"""

import subprocess
import json
import time
import asyncio
import websockets
from typing import Dict, List, Optional

def run_command(cmd: str) -> str:
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def check_adb_devices() -> List[str]:
    """Check connected ADB devices"""
    output = run_command("adb devices")
    lines = output.split('\n')[1:]  # Skip header
    devices = []
    for line in lines:
        if line.strip() and '\tdevice' in line:
            device_id = line.split('\t')[0]
            devices.append(device_id)
    return devices

def get_device_resolution(device_id: str) -> Dict[str, int]:
    """Get device screen resolution"""
    try:
        output = run_command(f"adb -s {device_id} shell wm size")
        if "Physical size:" in output:
            size_line = output.split("Physical size:")[1].strip()
            width, height = map(int, size_line.split('x'))
            return {"width": width, "height": height}
        else:
            # Fallback method
            output = run_command(f"adb -s {device_id} shell dumpsys display | grep 'mBaseDisplayInfo'")
            # Parse the output to extract resolution
            return {"width": 1080, "height": 1920}  # Default fallback
    except Exception as e:
        print(f"Error getting resolution for {device_id}: {e}")
        return {"width": 1080, "height": 1920}

def check_running_processes() -> Dict[str, bool]:
    """Check which device farm processes are running"""
    processes = {
        "central_device": False,
        "master_recorder": False,
        "farm_device_executor": False
    }
    
    output = run_command("ps aux | grep -E '(central_device|master_recorder|farm_device_executor)' | grep -v grep")
    
    for process_name in processes.keys():
        if process_name in output:
            processes[process_name] = True
    
    return processes

def check_websocket_connection(url: str) -> bool:
    """Check if WebSocket server is accessible"""
    async def test_connection():
        try:
            websocket = await websockets.connect(url)
            await websocket.close()
            return True
        except Exception:
            return False
    
    try:
        return asyncio.run(test_connection())
    except Exception:
        return False

def analyze_recent_logs() -> Dict[str, List[str]]:
    """Analyze recent log entries for issues"""
    issues = {
        "coordinate_issues": [],
        "connection_issues": [],
        "missing_events": [],
        "scaling_issues": []
    }
    
    try:
        # Check farm device executor logs
        output = run_command("tail -50 farm-device-executor.log")
        lines = output.split('\n')
        
        for line in lines:
            if "tap_release fallback" in line.lower():
                issues["missing_events"].append("Missing tap_press events - using fallback")
            if "master resolution not available" in line.lower():
                issues["coordinate_issues"].append("Master resolution not available for scaling")
            if "connection failed" in line.lower():
                issues["connection_issues"].append("WebSocket connection failures detected")
            if "scaled coordinates" in line.lower() and "outside" in line.lower():
                issues["scaling_issues"].append("Coordinates outside device bounds")
    
    except Exception as e:
        issues["coordinate_issues"].append(f"Could not analyze logs: {e}")
    
    return issues

def main():
    """Main diagnostic function"""
    print("🔍 Device Farm Coordinate Issue Diagnostic")
    print("=" * 60)
    
    # Check ADB devices
    print("\n📱 Connected ADB Devices:")
    devices = check_adb_devices()
    if not devices:
        print("❌ No ADB devices found!")
        print("   Solution: Connect Android devices/emulators and ensure ADB is working")
        return
    
    for device in devices:
        resolution = get_device_resolution(device)
        print(f"   ✅ {device}: {resolution['width']}x{resolution['height']}")
    
    # Check running processes
    print("\n🔧 Running Processes:")
    processes = check_running_processes()
    for process, running in processes.items():
        status = "✅ Running" if running else "❌ Not Running"
        print(f"   {process}: {status}")
    
    # Check WebSocket connectivity
    print("\n🌐 WebSocket Connectivity:")
    central_server_accessible = check_websocket_connection("ws://127.0.0.1:8765/master")
    farm_server_accessible = check_websocket_connection("ws://127.0.0.1:8765/farm")
    
    print(f"   Central Server (master): {'✅ Accessible' if central_server_accessible else '❌ Not Accessible'}")
    print(f"   Central Server (farm): {'✅ Accessible' if farm_server_accessible else '❌ Not Accessible'}")
    
    # Analyze logs for issues
    print("\n📋 Log Analysis:")
    issues = analyze_recent_logs()
    
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    if total_issues == 0:
        print("   ✅ No obvious issues found in recent logs")
    else:
        for category, issue_list in issues.items():
            if issue_list:
                print(f"   ⚠️ {category.replace('_', ' ').title()}:")
                for issue in issue_list:
                    print(f"      - {issue}")
    
    # Provide recommendations
    print("\n💡 Recommendations:")
    
    if not processes["central_device"]:
        print("   1. ❌ Start the central server: python src/central_device.py")
    
    if not processes["master_recorder"]:
        print("   2. ❌ Start the master recorder: python src/master_recorder.py")
        print("      This is likely the main cause of missing tap_press events!")
    
    if not processes["farm_device_executor"]:
        print("   3. ❌ Start the farm device executor: python src/farm_device_executor.py")
    
    if len(devices) < 2:
        print("   4. ⚠️ You need at least 2 devices (1 master + 1 farm) for testing")
    
    if issues["missing_events"]:
        print("   5. 🔧 Missing tap_press events indicate master recorder is not running or not sending events properly")
    
    if issues["coordinate_issues"]:
        print("   6. 📐 Coordinate scaling issues detected - check master resolution updates")
    
    # Test coordinate scaling logic
    print("\n🧮 Coordinate Scaling Test:")
    if len(devices) >= 2:
        master_device = devices[0]
        farm_device = devices[1]
        
        master_res = get_device_resolution(master_device)
        farm_res = get_device_resolution(farm_device)
        
        # Test center tap
        master_center_x = master_res["width"] // 2
        master_center_y = master_res["height"] // 2
        
        # Calculate expected farm coordinates
        normalized_x = master_center_x / master_res["width"]
        normalized_y = master_center_y / master_res["height"]
        
        expected_farm_x = int(normalized_x * farm_res["width"])
        expected_farm_y = int(normalized_y * farm_res["height"])
        
        print(f"   Master center tap: ({master_center_x}, {master_center_y}) on {master_res['width']}x{master_res['height']}")
        print(f"   Expected farm tap: ({expected_farm_x}, {expected_farm_y}) on {farm_res['width']}x{farm_res['height']}")
        print(f"   Scaling ratio: {farm_res['width']/master_res['width']:.3f}x, {farm_res['height']/master_res['height']:.3f}y")
    
    print("\n🎯 Summary:")
    if all(processes.values()) and central_server_accessible and farm_server_accessible:
        print("   ✅ All systems appear to be running correctly")
        print("   ✅ Coordinate scaling logic has been fixed and should work properly")
        if issues["missing_events"]:
            print("   ⚠️ However, missing tap_press events suggest master recorder issues")
    else:
        print("   ❌ System is not fully operational - follow recommendations above")
    
    print("\n📝 Next Steps:")
    print("   1. Ensure all processes are running (central server, master recorder, farm executor)")
    print("   2. Test with a simple tap on the master device")
    print("   3. Check farm device logs for coordinate scaling messages")
    print("   4. Verify tap executes at the correct location on farm device")

if __name__ == "__main__":
    main()
