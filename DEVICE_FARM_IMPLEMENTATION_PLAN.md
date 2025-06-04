# Device Farm Implementation Plan

## Overview
This plan outlines how to complete your device farm system for mobile app test automation where one master device controls multiple farm devices.

## Current System Status
- ✅ **Central Server** (`central-device.py`) - WebSocket hub for communication
- ✅ **Master Recorder** (`master-recorder.py`) - Captures actions from master device
- ❌ **Farm Device Executor** - Missing component to execute actions on farm devices

## System Architecture

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

## Implementation Phases

### Phase 1: Core System Completion (Week 1)

#### 1.1 Create Farm Device Executor (`farm-device-executor.py`)
**Purpose**: Connect to central server and execute received actions on farm devices

**Key Features**:
- Connect to central server via WebSocket (`/farm` endpoint)
- Receive action messages (tap, swipe, key press)
- Execute actions using ADB commands
- Handle device-specific coordinate scaling
- Report execution status back to central server

**Core Actions to Support**:
```python
# Touch Actions
{"action": "tap_press", "x": 100, "y": 200}   # adb shell input tap 100 200
{"action": "tap_release", "x": 100, "y": 200} # Complete tap action

# Key Actions  
{"action": "key_press", "key_code": "KEYCODE_BACK"}  # adb shell input keyevent 4

# Text Input (future)
{"action": "text_input", "text": "hello@example.com"}  # adb shell input text "hello@example.com"
```

#### 1.2 Add Coordinate Scaling System
**Problem**: Master device and farm devices may have different screen resolutions
**Solution**: Scale coordinates proportionally

```python
# Get device resolution: adb shell wm size
# Master: 1080x1920, Farm: 720x1280
# Scale factor: farm_x = master_x * (720/1080), farm_y = master_y * (1280/1920)
```

#### 1.3 Basic Testing Setup
- Test with 1 master + 1 farm device
- Verify tap actions replicate correctly
- Ensure coordinate scaling works

### Phase 2: Enhanced Functionality (Week 2-3)

#### 2.1 Advanced Action Support
- **Swipe/Scroll**: Convert to `adb shell input swipe x1 y1 x2 y2 duration`
- **Text Input**: Handle keyboard events and text entry
- **Multi-touch**: Support pinch/zoom gestures
- **Long Press**: Handle press and hold actions

#### 2.2 Device Management System
```python
# device-manager.py
- Auto-discover connected devices
- Track device status (online/offline/busy)
- Handle device reconnection
- Store device profiles (resolution, model, etc.)
```

#### 2.3 Error Handling & Resilience
- Reconnect on WebSocket disconnection
- Retry failed ADB commands
- Handle device disconnection gracefully
- Log all actions and errors

### Phase 3: Maestro Integration (Month 1)

#### 3.1 Maestro Command Bridge
**Purpose**: Convert low-level touch events to Maestro commands

```python
# maestro-bridge.py
# Convert recorded actions to Maestro YAML
tap_press + tap_release → tapOn: {x: 100, y: 200}
key_press KEYCODE_BACK → pressKey: Back
text_input "hello" → inputText: "hello"
```

#### 3.2 Session Recording & Playback
```python
# session-recorder.py
- Record complete user sessions
- Save as JSON or Maestro YAML
- Replay recorded sessions on demand
- Schedule automated playback
```

### Phase 4: Advanced Features (Month 2+)

#### 4.1 iOS Support
- Use `xcrun simctl` for iOS Simulator
- Use `ios-deploy` or WebDriverAgent for physical iOS devices
- Handle iOS-specific coordinate systems

#### 4.2 Web Dashboard (Optional)
- Real-time device monitoring
- Action logging and replay
- Device health status
- Test session management

## File Structure

```
device-farm/
├── central-device.py              # ✅ Existing - Central WebSocket server
├── master-recorder.py             # ✅ Existing - Records master device actions
├── farm-device-executor.py        # ❌ NEW - Executes actions on farm devices
├── device-manager.py              # ❌ NEW - Device discovery and management
├── coordinate-scaler.py           # ❌ NEW - Handle screen resolution differences
├── maestro-bridge.py              # ❌ NEW - Convert to Maestro commands
├── session-recorder.py            # ❌ NEW - Record/playback sessions
├── config/
│   ├── devices.json              # Device configurations
│   └── scaling-profiles.json     # Screen scaling profiles
├── web-dashboard/                # Optional web interface
│   ├── index.html
│   ├── app.js
│   └── style.css
├── logs/                         # Action and error logs
└── scripts/
    ├── start-farm.sh             # Start all components
    ├── setup-devices.sh          # Device setup automation
    └── test-connection.sh        # Connection testing
```

## Quick Start Commands

```bash
# Terminal 1: Start Central Server
python central-device.py

# Terminal 2: Start Master Recorder (connect master device)
python master-recorder.py

# Terminal 3: Start Farm Device Executor (for each farm device)
python farm-device-executor.py --device-id emulator-5554

# Terminal 4: Start another Farm Device
python farm-device-executor.py --device-id emulator-5556

# Optional: Web Dashboard
python -m http.server 8080 --directory web-dashboard
```

## Implementation Priority

### Immediate (This Week)
1. **Create `farm-device-executor.py`** - Core functionality
2. **Add coordinate scaling** - Handle different screen sizes  
3. **Test basic replication** - Verify tap actions work

### Next Steps (Week 2)
4. **Add text input support** - Handle keyboard events
5. **Improve error handling** - Robust connection management
6. **Device management** - Better device discovery

### Future Enhancements
7. **Maestro integration** - Generate Maestro test files
8. **Session recording** - Save and replay sessions
9. **iOS support** - Extend to iOS devices
10. **Web dashboard** - Visual monitoring interface

## Key Benefits

1. **No External Dependencies** - Uses standard ADB commands
2. **Real-time Replication** - Actions execute immediately
3. **Scalable** - Support unlimited farm devices
4. **Cross-platform Ready** - Architecture supports Android/iOS
5. **Maestro Compatible** - Can generate Maestro YAML files
6. **Tool Agnostic** - Works with any mobile app

## Technical Considerations

### Screen Resolution Handling
```python
# Get device resolution
adb shell wm size
# Output: Physical size: 1080x1920

# Calculate scaling factors
master_width, master_height = 1080, 1920
farm_width, farm_height = 720, 1280
scale_x = farm_width / master_width    # 0.667
scale_y = farm_height / master_height  # 0.667

# Apply scaling
farm_x = int(master_x * scale_x)
farm_y = int(master_y * scale_y)
```

### Action Execution
```python
# Basic tap execution
def execute_tap(x, y, device_id):
    cmd = f"adb -s {device_id} shell input tap {x} {y}"
    subprocess.run(cmd.split())

# Text input execution  
def execute_text_input(text, device_id):
    cmd = f"adb -s {device_id} shell input text '{text}'"
    subprocess.run(cmd.split())
```

### WebSocket Communication
```python
# Farm device connects to central server
websocket = await websockets.connect("ws://central-server:8765/farm")

# Listen for actions
async for message in websocket:
    action = json.loads(message)
    if action['action'] == 'tap_press':
        execute_tap(action['x'], action['y'], device_id)
```

This plan provides a complete roadmap to transform your current system into a fully functional device farm for mobile app test automation.