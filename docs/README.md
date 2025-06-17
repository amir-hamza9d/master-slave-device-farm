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

1.  **Python 3.9+**
2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Android SDK Platform Tools** (for ADB):
    *   Download from: [https://developer.android.com/studio/releases/platform-tools](https://developer.android.com/studio/releases/platform-tools)
    *   Ensure `adb` is installed and accessible in your system's PATH.
4.  **Connected Android Devices**:
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

## 🎮 Usage Guide

1.  **Initiate all components** using either the automated or manual setup methods.
2.  **Confirm Connections**: Observe the console outputs:
    *   Central server will display connected device IDs.
    *   Master recorder will show "GETEVENT MONITOR STARTED".
    *   Farm executors will indicate "FARM DEVICE READY".
3.  **Interact with the Master Device**: Perform any desired actions such as tapping, swiping, typing, or pressing hardware buttons.
4.  **Observe Replication**: Watch as all connected farm devices seamlessly replicate the actions performed on the master device.

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
*   **Connection Issues**:
    *   Confirm all devices are listed by `adb devices`.
    *   Check firewall settings for WebSocket connections (port 8765 by default).
    *   Ensure the central server's IP address is reachable from all devices.
*   **Coordinate Scaling Discrepancies**:
    *   The system automatically handles coordinate scaling. Review logs for scaling factor information if issues arise.

## 📊 Monitoring

*   **Real-time Logs**: Each component (Central Server, Master Recorder, Farm Executors) provides detailed console logs for monitoring connections, captured events, and executed actions.
*   **Status Check**: Use the `start-device-farm.sh` script and select option `5` ("Show Status") for an overview of active components and connected devices.

## 🔮 Advanced Configuration

*   **Custom Device Selection**: Specify a device ID or an index from `adb devices` when launching `farm-device-executor.py`.
    ```bash
    python3 farm-device-executor.py emulator-5554
    python3 farm-device-executor.py 1 # (for the first device in `adb devices` list)
    ```
*   **Network Configuration**: Modify the `CENTRAL_SERVER_URL` variable in `master-recorder.py` and `farm-device-executor.py` to adjust the WebSocket server address.
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