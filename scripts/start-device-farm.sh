#!/bin/bash

# Device Farm Startup Script
# This script helps you start all components of the device farm system

echo "🚀 Device Farm Startup Script"
echo "=============================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python3 is required but not installed"
    exit 1
fi

if ! command_exists adb; then
    echo "❌ ADB is required but not installed"
    echo "Please install Android SDK Platform Tools"
    exit 1
fi

echo "✅ Dependencies check passed"
echo ""

# Check connected devices
echo "📱 Checking connected devices..."
adb devices -l
echo ""

# Get available devices
devices=$(adb devices | grep -v "List of devices" | grep "device$" | cut -f1)
device_count=$(echo "$devices" | wc -w)

if [ $device_count -eq 0 ]; then
    echo "❌ No devices connected. Please connect at least 2 devices (1 master + 1+ farm devices)"
    exit 1
elif [ $device_count -eq 1 ]; then
    echo "⚠️  Only 1 device connected. You need at least 2 devices (1 master + 1+ farm devices)"
    echo "You can still test with 1 device, but actions won't be replicated"
fi

echo "✅ Found $device_count connected device(s)"
echo ""

# Show menu
echo "🎯 Device Farm Components:"
echo "1. Central Server (required - start first)"
echo "2. Master Recorder (connects to master device)"
echo "3. Farm Device Executor (connects to farm devices)"
echo "4. Start All (automated setup)"
echo "5. Show Status"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo "🏢 Starting Central Server..."
        echo "This will start the WebSocket server that coordinates all devices"
        echo "Keep this terminal open and running"
        echo ""
        # Ask which central server implementation to use
        echo "Select central server implementation:"
        echo "1. central-device.py (original)"
        echo "2. central-device-router.py (improved router)"
        read -p "Select option (1-2, default: 2): " server_choice
        
        if [ "$server_choice" = "1" ]; then
            python3 central-device.py
        else
            python3 central-device-router.py
        fi
        ;;
    2)
        echo "📱 Starting Master Recorder..."
        echo "This will connect to your master device and capture touch/key events"
        echo "Make sure the Central Server is running first!"
        echo ""
        python3 master-recorder.py
        ;;
    3)
        echo "🤖 Starting Farm Device Executor..."
        echo "Available devices:"
        i=1
        for device in $devices; do
            device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
            echo "  $i. $device ($device_model)"
            i=$((i+1))
        done
        echo ""
        read -p "Enter device number or device ID for farm device: " device_input
        
        # Check if input is a number
        if [[ $device_input =~ ^[0-9]+$ ]]; then
            # Convert number to device ID
            device_array=($devices)
            selected_device=${device_array[$((device_input-1))]}
        else
            # Use as device ID directly
            selected_device=$device_input
        fi
        
        if [ -z "$selected_device" ]; then
            echo "❌ Invalid device selection"
            exit 1
        fi
        
        # Ask for master device to exclude
        echo ""
        echo "Select master device to exclude (this device will NOT receive actions):"
        i=1
        for device in $devices; do
            if [ "$device" != "$selected_device" ]; then
                device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
                echo "  $i. $device ($device_model)"
                i=$((i+1))
            fi
        done
        echo "  n. None (no master device to exclude)"
        echo ""
        read -p "Enter master device number/ID or 'n' for none: " master_input
        
        master_device=""
        if [ "$master_input" != "n" ] && [ "$master_input" != "N" ] && [ -n "$master_input" ]; then
            if [[ $master_input =~ ^[0-9]+$ ]]; then
                # Convert number to device ID
                device_array=($devices)
                master_device=${device_array[$((master_input-1))]}
            else
                # Use as device ID directly
                master_device=$master_input
            fi
            
            echo "🚫 Will exclude master device: $master_device"
            master_param="--master $master_device"
        else
            echo "No master device will be excluded"
            master_param=""
        fi
        
        echo "🤖 Starting Farm Device Executor for device: $selected_device"
        echo "Make sure the Central Server is running first!"
        echo ""
        python3 farm-device-executor.py $master_param $selected_device
        ;;
    4)
        echo "🚀 Starting All Components (Automated Setup)"
        echo "This will open multiple terminal windows/tabs"
        echo ""
        
        # Check if we're in a terminal that supports opening new tabs/windows
        if command_exists gnome-terminal; then
            echo "Using gnome-terminal..."
            
            # Ask which central server implementation to use
            echo "Select central server implementation:"
            echo "1. central-device.py (original)"
            echo "2. central-device-router.py (improved router)"
            read -p "Select option (1-2, default: 2): " server_choice
            
            central_server="central-device-router.py"
            if [ "$server_choice" = "1" ]; then
                central_server="central-device.py"
            fi
            
            # Start Central Server
            gnome-terminal --tab --title="Central Server" -- bash -c "echo '🏢 Central Server'; python3 $central_server; read -p 'Press Enter to close...'"
            
            sleep 2
            
            # Prompt for master device selection
            echo "Select master device:"
            i=1
            device_array=($devices)
            for device in "${device_array[@]}"; do
                device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
                echo "  $i. $device ($device_model)"
                i=$((i+1))
            done
            
            read -p "Enter master device number (default: 1): " master_choice
            if [ -z "$master_choice" ] || ! [[ "$master_choice" =~ ^[0-9]+$ ]]; then
                master_choice=1
            fi
            
            master_device=${device_array[$((master_choice-1))]}
            echo "Selected master device: $master_device"
            
            # Start Master Recorder
            gnome-terminal --tab --title="Master Recorder" -- bash -c "echo '📱 Master Recorder'; python3 master-recorder.py; read -p 'Press Enter to close...'"
            
            # Start Farm Device Executors for each device except the master
            for device in "${device_array[@]}"; do
                if [ "$device" != "$master_device" ]; then
                    device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
                    gnome-terminal --tab --title="Farm Device: $device" -- bash -c "echo '🤖 Farm Device: $device ($device_model)'; python3 farm-device-executor.py --master $master_device $device; read -p 'Press Enter to close...'"
                fi
            done
            
        elif command_exists xterm; then
            echo "Using xterm..."
            
            # Use the same central server as selected above
            if [ -z "$central_server" ]; then
                central_server="central-device-router.py"
                if [ "$server_choice" = "1" ]; then
                    central_server="central-device.py"
                fi
            fi
            
            xterm -title "Central Server" -e "python3 $central_server" &
            sleep 2
            
            # Prompt for master device if not already selected
            if [ -z "$master_device" ]; then
                echo "Select master device:"
                i=1
                device_array=($devices)
                for device in "${device_array[@]}"; do
                    device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
                    echo "  $i. $device ($device_model)"
                    i=$((i+1))
                done
                
                read -p "Enter master device number (default: 1): " master_choice
                if [ -z "$master_choice" ] || ! [[ "$master_choice" =~ ^[0-9]+$ ]]; then
                    master_choice=1
                fi
                
                master_device=${device_array[$((master_choice-1))]}
                echo "Selected master device: $master_device"
            fi
            
            xterm -title "Master Recorder" -e "python3 master-recorder.py" &
            
            # Start Farm Device Executors for each device except the master
            device_array=($devices)
            for device in "${device_array[@]}"; do
                if [ "$device" != "$master_device" ]; then
                    xterm -title "Farm Device: $device" -e "python3 farm-device-executor.py --master $master_device $device" &
                fi
            done
            
        else
            echo "⚠️  Automatic terminal opening not supported"
            echo "Please manually run these commands in separate terminals:"
            echo ""
            
            # Use the same central server as selected above
            if [ -z "$central_server" ]; then
                echo "Select central server implementation:"
                echo "1. central-device.py (original)"
                echo "2. central-device-router.py (improved router)"
                read -p "Select option (1-2, default: 2): " server_choice
                
                central_server="central-device-router.py"
                if [ "$server_choice" = "1" ]; then
                    central_server="central-device.py"
                fi
            fi
            
            echo "Terminal 1: python3 $central_server"
            echo "Terminal 2: python3 master-recorder.py"
            
            # Prompt for master device if not already selected
            if [ -z "$master_device" ]; then
                echo "Select master device:"
                i=1
                device_array=($devices)
                for device in "${device_array[@]}"; do
                    device_model=$(adb -s $device shell getprop ro.product.model 2>/dev/null | tr -d '\r')
                    echo "  $i. $device ($device_model)"
                    i=$((i+1))
                done
                
                read -p "Enter master device number (default: 1): " master_choice
                if [ -z "$master_choice" ] || ! [[ "$master_choice" =~ ^[0-9]+$ ]]; then
                    master_choice=1
                fi
                
                master_device=${device_array[$((master_choice-1))]}
                echo "Selected master device: $master_device"
            fi
            
            # Show commands for farm devices
            terminal_num=3
            device_array=($devices)
            for device in "${device_array[@]}"; do
                if [ "$device" != "$master_device" ]; then
                    echo "Terminal $terminal_num: python3 farm-device-executor.py --master $master_device $device"
                    terminal_num=$((terminal_num+1))
                fi
            done
        fi
        ;;
    5)
        echo "📊 Device Farm Status"
        echo "===================="
        echo ""
        echo "📁 Files:"
        ls -la *.py
        echo ""
        echo "📱 Connected Devices:"
        adb devices -l
        echo ""
        echo "🌐 Network:"
        echo "Central Server should be running on: ws://$(hostname -I | awk '{print $1}'):8765"
        echo ""
        echo "🔄 Processes:"
        ps aux | grep -E "(central-device|master-recorder|farm-device)" | grep -v grep
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac