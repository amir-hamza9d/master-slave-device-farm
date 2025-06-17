# Device Farm - Unified Mobile Test Automation

## 🌟 Project Overview

The Device Farm is an innovative system designed to streamline mobile application testing and demonstrations across multiple Android devices simultaneously. It enables users to perform actions on a single "master" device, and these actions are instantly replicated in real-time across all connected "farm" devices. This ensures consistent testing, efficient demonstrations, and comprehensive compatibility checks without repetitive manual input on each device.

## 📖 How It Works: A User's Journey

Imagine you're a mobile app developer or a QA engineer. You've just built an amazing new feature, and you need to see how it behaves on various Android phones and tablets. Instead of picking up each device one by one, tapping, swiping, and typing the same things over and over, you simply connect all your devices to the Device Farm.

You pick up your designated "master" device – perhaps your primary test phone. As you interact with it, navigating through your app, tapping buttons, or typing in forms, a silent observer captures every move. This observer then sends these actions to a central coordinator.

The coordinator, acting like a conductor, instantly broadcasts these instructions to all the other "farm" devices you've connected. On these farm devices, tiny digital hands spring into action, mimicking your every tap, swipe, and keystroke in perfect synchronicity. You watch as your app responds identically across a fleet of devices, confirming its behavior, identifying layout issues, or simply showcasing its functionality to an audience, all from the comfort of interacting with just one device. It's like having a team of invisible testers working in unison, ensuring your app performs flawlessly everywhere.

## 🛠️ Technology Stack and Dependencies

This project leverages standard Android Debug Bridge (ADB) commands for device interaction and Python for its core logic and communication.

*   **Python**: Version 3.9.x or higher
    *   **`websockets`**: Version 12.0 (for real-time communication between components)
        ```bash
        pip install websockets==12.0
        ```
*   **Android SDK Platform Tools**: (Includes ADB)
    *   Ensure `adb` is installed and accessible in your system's PATH.
    *   Download from: [Android Developers - Platform Tools](https://developer.android.com/studio/releases/platform-tools)

## ✨ Key Features

*   **Real-time Action Replication**: Instantly mirrors interactions from the master device to all farm devices.
*   **Comprehensive Event Support**: Captures and replicates touch events (tap, long press, swipe), key events (back, home, volume), and text input.
*   **Automatic Coordinate Scaling**: Intelligently adjusts touch coordinates to accommodate devices with varying screen resolutions, ensuring accurate replication across diverse form factors.
*   **Simplified Setup**: Includes a helper script (`start-device-farm.sh`) for automated component startup.
*   **ADB-Native**: Relies solely on standard ADB commands, eliminating the need for complex third-party tools or frameworks.

## 🏗️ System Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   Master Device │ ────────────────▶│ Central Server  │
│ (manual actions)│                  │   (hub/router)  │
└─────────────────┘                  └─────────────────┘
                                               │
                                               ▼ Broadcast
                                     ┌─────────────────┐
                                     │  Farm Device 1  │
                                     │  Farm Device 2  │
                                     │  Farm Device N  │
                                     └─────────────────┘
```

## 📁 Project Structure

*   **`central-device.py`**: The core WebSocket server responsible for coordinating communication and broadcasting actions to all connected devices.
*   **`master-recorder.py`**: Captures touch and key events from the designated master device and sends them to the central server.
*   **`farm-device-executor.py`**: Receives actions from the central server and executes them on individual farm devices using ADB commands.
*   **`start-device-farm.sh`**: A convenient shell script to automate the startup of all necessary components.
*   **`DEVICE_FARM_IMPLEMENTATION_PLAN.md`**: Detailed documentation outlining the implementation strategy and design choices.
*   **`config.json`**: Configuration file for system parameters (e.g., WebSocket server address).
*   **`test_central_device_router.py`**: Unit tests for the central device routing logic.

## 🚀 Quick Start

### Prerequisites

1.  **Python 3.9+** with `websockets` library:
    ```bash
    pip install websockets==12.0
    ```
2.  **Android SDK Platform Tools** (for ADB):
    *   Download from: [https://developer.android.com/studio/releases/platform-tools](https://developer.android.com/studio/releases/platform-tools)
    *   Add to your system's PATH or place `adb` executable in the project directory.
3.  **Connected Android Devices**:
    *   At least 2 devices (1 master + 1+ farm devices).
    *   Enable USB Debugging on all devices.
    *   Verify connectivity with: `adb devices`

### Method 1: Automated Setup (Recommended)

```bash
# Make the script executable (if not already)
chmod +x start-device-farm.sh

# Run the startup script
./start-device-farm.sh
```
Select option `4` for "Start All" to automatically launch all components.

### Method 2: Manual Setup

**Terminal 1 - Central Server:**
```bash
python3 central-device.py
```

**Terminal 2 - Master Recorder:**
```bash
python3 master-recorder.py
```

**Terminal 3+ - Farm Device Executors (one per farm device):**
```bash
# For first farm device
python3 farm-device-executor.py emulator-5554

# For second farm device
python3 farm-device-executor.py emulator-5556

# Or let it auto-detect the first available device
python3 farm-device-executor.py
```

## 🎛️ Command Line Options

### Quick Reference Table

| Script | Flag | Description | Example |
|--------|------|-------------|---------|
| `master-recorder.py` | `--debug` | Enable verbose event logging | `python3 master-recorder.py --debug` |
| `farm-device-executor.py` | `--debug` | Enable verbose action logging | `python3 farm-device-executor.py --debug` |
| `farm-device-executor.py` | `--master DEVICE` | Exclude master device from farm | `python3 farm-device-executor.py --master emulator-5554` |
| `farm-device-executor.py` | `--server URL` | Custom WebSocket server URL | `python3 farm-device-executor.py --server ws://192.168.1.100:8765/farm` |
| `farm-device-executor.py` | `--log-level LEVEL` | Set logging level | `python3 farm-device-executor.py --log-level WARNING` |
| `farm-device-executor.py` | `devices...` | Specify target devices | `python3 farm-device-executor.py emulator-5556 emulator-5558` |

### Master Recorder (`master-recorder.py`)

```bash
python3 master-recorder.py [OPTIONS]
```

**Available Options:**
- `--help`, `-h` - Show help message and exit
- `--debug` - Enable debug mode with verbose logging

**Usage Examples:**
```bash
# Normal mode (clean output)
python3 master-recorder.py

# Debug mode (shows RAW EVENT, PARSED logs, touch coordinates, etc.)
python3 master-recorder.py --debug
```

**Debug Mode Features:**
- 📱 RAW EVENT logs for every input event
- 🔍 PARSED event details with device path, type, code, and value
- 👆 Touch coordinate tracking (X/Y positions)
- 👆 Finger state changes (UP/DOWN/PRESS)
- 🚀 Action sending details to central server
- ⌨️ Key press/release events

### Farm Device Executor (`farm-device-executor.py`)

```bash
python3 farm-device-executor.py [OPTIONS] [devices...]
```

**Available Options:**
- `--help`, `-h` - Show help message and exit
- `--server SERVER` - Central server URL (default: `ws://127.0.0.1:8765/farm`)
- `--master MASTER` - Master device ID to exclude from farm (optional)
- `--debug` - Enable debug mode with verbose logging
- `--log-level {DEBUG,INFO,WARNING,ERROR}` - Set log level (default: INFO)
- `devices` - Specific device IDs to use (optional positional arguments)

**Usage Examples:**
```bash
# Normal mode - auto-discover all devices
python3 farm-device-executor.py

# Debug mode - verbose action execution logging
python3 farm-device-executor.py --debug

# Specify master device to exclude from farm
python3 farm-device-executor.py --master emulator-5554

# Use only specific devices
python3 farm-device-executor.py emulator-5556 emulator-5558

# Custom server URL
python3 farm-device-executor.py --server ws://192.168.1.100:8765/farm

# Combine multiple options
python3 farm-device-executor.py --debug --master emulator-5554 --server ws://localhost:8765/farm emulator-5556 emulator-5558

# Set specific log level without debug mode
python3 farm-device-executor.py --log-level WARNING
```

**Debug Mode Features:**
- 📡 RECEIVED action details from central server
- 🎯 TAP EXECUTED confirmations with coordinates
- ⌨️ KEY EXECUTED confirmations
- 📝 TEXT EXECUTED confirmations
- 👆 TAP PRESS STORED intermediate states
- All internal debug logging messages

## 🎮 Usage Guide

1.  **Initiate all components** using either the automated or manual setup methods.
2.  **Confirm Connections**: Observe the console outputs:
    *   Central server will display connected device IDs.
    *   Master recorder will show "GETEVENT MONITOR STARTED".
    *   Farm executors will indicate "FARM DEVICE READY".
3.  **Interact with the Master Device**: Perform any desired actions such as tapping, swiping, typing, or pressing hardware buttons.
4.  **Observe Replication**: Watch as all connected farm devices seamlessly replicate the actions performed on the master device.

## 🎯 Complete Workflow Examples

### Basic Setup (2 devices)
```bash
# Terminal 1: Start central server
python3 central-device.py

# Terminal 2: Start master recorder (clean output)
python3 master-recorder.py

# Terminal 3: Start farm executor (auto-exclude master)
python3 farm-device-executor.py --master emulator-5554
```

### Debug Mode Setup (for troubleshooting)
```bash
# Terminal 1: Start central server
python3 central-device.py

# Terminal 2: Master recorder with verbose debugging
python3 master-recorder.py --debug

# Terminal 3: Farm executor with verbose debugging
python3 farm-device-executor.py --debug --master emulator-5554
```

### Advanced Multi-Device Setup
```bash
# Terminal 1: Start central server
python3 central-device.py

# Terminal 2: Master recorder (normal mode)
python3 master-recorder.py

# Terminal 3: Farm executor managing specific devices
python3 farm-device-executor.py --master emulator-5554 emulator-5556 emulator-5558 emulator-5560
```

### Custom Network Configuration
```bash
# Terminal 1: Start central server on custom port
python3 central-device.py --port 9000

# Terminal 2: Master recorder connecting to custom server
python3 master-recorder.py

# Terminal 3: Farm executor with custom server URL
python3 farm-device-executor.py --server ws://192.168.1.100:9000/farm --master emulator-5554
```

## 📱 Device Setup

### Android Emulators
```bash
# Example: Start multiple emulators
emulator -avd Pixel_4_API_30 -port 5554
emulator -avd Pixel_4_API_30 -port 5556
```

### Physical Devices
1.  Enable Developer Options on your Android device.
2.  Enable USB Debugging within Developer Options.
3.  Connect the device to your computer via USB.
4.  Accept any debugging authorization prompts on the device.

### Verify Device Connection
```bash
adb devices
# Expected output (example):
# List of devices attached
# emulator-5554    device
# emulator-5556    device
# 123456789ABCDEF  device
```

## 🐛 Troubleshooting

*   **No Events Detected**:
    *   Ensure the master device has appropriate ADB permissions.
    *   Try running `master-recorder.py` with `sudo` if permission issues persist.
    *   Verify `getevent` functionality: `adb shell getevent`.
    *   **Enable debug mode** to see detailed event capture: `python3 master-recorder.py --debug`
*   **Connection Issues**:
    *   Confirm all devices are listed by `adb devices`.
    *   Check firewall settings for WebSocket connections (port 8765 by default).
    *   Ensure the central server's IP address is reachable from all devices.
    *   **Use debug mode** to see connection details: `python3 farm-device-executor.py --debug`
*   **Coordinate Scaling Discrepancies**:
    *   The system automatically handles coordinate scaling. Review logs for scaling factor information if issues arise.
    *   **Enable debug mode** to see coordinate transformation details: `python3 farm-device-executor.py --debug`
*   **Actions Not Executing on Farm Devices**:
    *   Verify farm devices are properly connected and authorized for ADB.
    *   Check that the master device is correctly excluded: `python3 farm-device-executor.py --master DEVICE_ID`
    *   **Use debug mode** to see received actions and execution status: `python3 farm-device-executor.py --debug`
*   **Performance Issues**:
    *   In production use, avoid debug mode as it generates verbose output.
    *   Use `--log-level WARNING` or `--log-level ERROR` to reduce log verbosity.
*   **Multiple Device Management**:
    *   Specify exact devices to avoid conflicts: `python3 farm-device-executor.py device1 device2 device3`
    *   Always specify the master device to prevent it from being included in the farm.

## 📊 Monitoring

*   **Real-time Logs**: Each component (Central Server, Master Recorder, Farm Executors) provides detailed console logs for monitoring connections, captured events, and executed actions.
*   **Debug Mode Monitoring**: Enable verbose logging for detailed troubleshooting:
    ```bash
    # Detailed event capture and parsing
    python3 master-recorder.py --debug

    # Detailed action execution and coordination
    python3 farm-device-executor.py --debug
    ```
*   **Log Level Control**: Adjust verbosity for different scenarios:
    ```bash
    # Production mode (minimal logs)
    python3 farm-device-executor.py --log-level ERROR

    # Development mode (detailed logs)
    python3 farm-device-executor.py --log-level DEBUG
    ```
*   **Status Check**: Use the `start-device-farm.sh` script and select option `5` ("Show Status") for an overview of active components and connected devices.

## 🔮 Advanced Configuration

*   **Custom Device Selection**: Specify device IDs when launching `farm-device-executor.py`.
    ```bash
    # Use specific devices only
    python3 farm-device-executor.py emulator-5554 emulator-5556

    # Auto-discover but exclude master
    python3 farm-device-executor.py --master emulator-5554
    ```
*   **Network Configuration**: Use the `--server` flag to specify custom WebSocket server addresses.
    ```bash
    # Custom server URL
    python3 farm-device-executor.py --server ws://192.168.1.100:8765/farm

    # Custom port
    python3 farm-device-executor.py --server ws://localhost:9000/farm
    ```
*   **Logging Configuration**: Control log verbosity for production or debugging scenarios.
    ```bash
    # Minimal logging for production
    python3 farm-device-executor.py --log-level ERROR

    # Verbose debugging
    python3 master-recorder.py --debug
    python3 farm-device-executor.py --debug

    # Custom log level without debug mode
    python3 farm-device-executor.py --log-level WARNING
    ```
*   **Master Device Management**: The system supports automatic master device detection and exclusion.
    ```bash
    # Explicitly specify master device
    python3 farm-device-executor.py --master emulator-5554

    # Let the system auto-detect master (if master-recorder.py is running)
    python3 farm-device-executor.py
    ```
*   **Single Master Device**: The current architecture supports one master device at a time. To switch masters, stop the current `master-recorder.py` and restart it on the new desired master device.

## 🎯 Use Cases and Benefits

*   **Accelerated Mobile App Testing**: Execute test cases across multiple devices simultaneously, drastically reducing manual effort and testing time.
*   **Efficient Demo Presentations**: Showcase application features on several screens at once, ideal for client presentations or team reviews.
*   **Cross-Device Compatibility Testing**: Quickly identify UI/UX inconsistencies and functional issues across different Android versions, screen sizes, and device manufacturers.
*   **Training and Onboarding**: Provide interactive demonstrations for new users or team members, allowing them to follow along on their own devices.
*   **Load Simulation (Basic)**: Simulate concurrent user interactions for basic load testing scenarios.

## 🤝 Contributing and Future Enhancements

This project provides a robust foundation for multi-device automation. Contributions are welcome to extend its capabilities, including:

*   **iOS Device Support**: Integrate support for Apple iOS devices.
*   **Web-based Dashboard**: Develop a user-friendly web interface for monitoring and control.
*   **Session Recording & Playback**: Implement functionality to record interaction sessions and play them back later.
*   **Advanced Gesture Recognition**: Enhance event capture to include more complex gestures.
*   **Multi-Master Device Support**: Architect support for multiple simultaneous master devices.
*   **Automated Test Script Generation**: Generate executable test scripts from recorded actions.

## 📄 License

This project is open-source, provided under an MIT-style license. Feel free to use, modify, and distribute it as needed for your testing and automation requirements.

---

**Happy Testing! 🚀**

For questions or issues, refer to the detailed logs generated by each component for comprehensive debugging information.