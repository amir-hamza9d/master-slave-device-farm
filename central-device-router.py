import asyncio
import websockets
import json
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("CentralServer")

# Store connected clients and their info
farm_devices: Dict[str, object] = {}  # Store device_id -> websocket object
farm_device_info: Dict[str, Dict] = {}  # Store device_id -> device info
master_device_websocket: Optional[object] = None # Store the master's websocket object
master_device_id: Optional[str] = None # Store the master's device ID
master_device_info: Optional[Dict] = None # Store the master's full device info

async def broadcast_to_farm_devices(message):
    """Send a message to all connected farm devices"""
    if farm_devices:
        disconnected_ids = []
        successful_broadcasts = 0
        
        # Parse the message to get action type for logging
        try:
            data = json.loads(message)
            action_type = data.get('action', 'unknown')
        except json.JSONDecodeError:
            action_type = "unknown"
            
        # Broadcast to all farm devices
        for device_id, websocket in list(farm_devices.items()): # Iterate over a copy
            logger.debug(f"Attempting to send message to farm device: {device_id}")
            try:
                await websocket.send(message)
                successful_broadcasts += 1
                logger.debug(f"Sent {action_type} to farm device: {device_id}")
                
            except websockets.exceptions.ConnectionClosed:
                disconnected_ids.append(device_id)
                logger.warning(f"Connection closed while sending to farm device: {device_id}")
            except Exception as e:
                disconnected_ids.append(device_id)
                logger.error(f"Error sending to farm device {device_id}: {e}")
        
        # Remove disconnected devices
        for device_id in disconnected_ids:
            if device_id in farm_devices:
                del farm_devices[device_id]
                if device_id in farm_device_info:
                    del farm_device_info[device_id]
                logger.info(f"Removed disconnected farm device: {device_id}")
                
        # Log broadcast summary
        if successful_broadcasts > 0:
            logger.info(f"Successfully broadcasted {action_type} to {successful_broadcasts} farm device(s)")
        else:
            logger.warning(f"Failed to broadcast {action_type} to any farm devices (0/{len(farm_devices)} connected)")
            
    else:
        logger.warning("No farm devices connected. Action not replicated.")

async def handle_master_device(websocket):
    """Handle messages from the master device"""
    global master_device_websocket, master_device_id, master_device_info
    master_device_websocket = websocket
    client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'Unknown'
    logger.info(f"Master device connected: {client_address}")
    print(f"🎮 MASTER DEVICE CONNECTED: {client_address}")
    
    try:
        async for message in websocket:
            try:
                # Parse the message
                data = json.loads(message)
                
                # Handle device info message
                if data.get('action') == 'device_info' and data.get('role') == 'master':
                    master_device_info = data.get('device_info')
                    master_device_id = master_device_info.get('id', 'Unknown')
                    device_model = master_device_info.get('model', 'Unknown')
                    device_version = master_device_info.get('android_version', 'Unknown')
                    logger.info(f"Master device info: {device_model} (Android {device_version}, ID: {master_device_id})")
                    
                    # If this master device was somehow added as a farm device, remove it
                    if master_device_id in farm_devices:
                        del farm_devices[master_device_id]
                        if master_device_id in farm_device_info:
                            del farm_device_info[master_device_id]
                        logger.warning(f"Master device {master_device_id} was incorrectly in farm_devices, removed.")
                    continue  # Don't broadcast device info messages
                
                logger.info(f"Received action from master: {data}")
                
                # Print action to console for visibility
                action_type = data.get('action', 'unknown')
                if 'x' in data and 'y' in data:
                    print(f"🎯 ACTION RECEIVED: {action_type} at ({data['x']}, {data['y']})")
                else:
                    print(f"🎯 ACTION RECEIVED: {action_type}")
                
                # Broadcast the action to all farm devices
                await broadcast_to_farm_devices(message)
                print(f"📡 BROADCASTED to {len(farm_devices)} farm device(s)")
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON from master: {message}")
            except Exception as e:
                logger.error(f"Error processing message from master: {e}")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Master device disconnected: {client_address}")
    except Exception as e:
        logger.error(f"Unexpected error with master device: {e}")
    finally:
        master_device_websocket = None
        master_device_id = None
        master_device_info = None

async def handle_farm_device(websocket):
    """Handle connection from a farm device"""
    client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'Unknown'
    logger.info(f"Farm device connected: {client_address}")
    print(f"🤖 FARM DEVICE CONNECTED: {client_address}")
    
    current_farm_device_id: Optional[str] = None

    try:
        # Keep the connection open and handle any messages
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Handle device info message
                if data.get('action') == 'device_info' and data.get('role') == 'farm':
                    device_info = data.get('device_info', {})
                    device_id = device_info.get('id', 'Unknown')
                    
                    if master_device_id and device_id == master_device_id:
                        logger.info(f"Farm device {device_id} is actually the master device. Not adding to farm_devices.")
                        # Close this connection as it's the master trying to connect as a farm device
                        await websocket.close(1000, "Master device attempting to connect as farm device.")
                        return # Exit handler for this websocket
                    
                    current_farm_device_id = device_id
                    farm_devices[device_id] = websocket
                    farm_device_info[device_id] = device_info
                    
                    device_model = device_info.get('model', 'Unknown')
                    device_version = device_info.get('android_version', 'Unknown')
                    logger.info(f"Farm device info: {device_model} (Android {device_version}, ID: {device_id})")
                else:
                    logger.warning(f"Received unexpected message from farm device {current_farm_device_id or client_address}: {data}")
            except json.JSONDecodeError:
                logger.error(f"Received invalid JSON from farm device {current_farm_device_id or client_address}: {message}")
            except Exception as e:
                logger.error(f"Error processing message from farm device {current_farm_device_id or client_address}: {e}")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Farm device disconnected: {current_farm_device_id or client_address}")
    except Exception as e:
        logger.error(f"Unexpected error with farm device {current_farm_device_id or client_address}: {e}")
    finally:
        # Remove from the set of farm devices
        if current_farm_device_id and current_farm_device_id in farm_devices:
            del farm_devices[current_farm_device_id]
        if current_farm_device_id and current_farm_device_id in farm_device_info:
            del farm_device_info[current_farm_device_id]

async def main():
    server_host = "0.0.0.0"
    server_port = 8765

    logger.info(f"Starting Central Server on ws://{server_host}:{server_port}")
    
    # Print local IP addresses for easier connection
    try:
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"Local IP address: {ip_address}")
        logger.info(f"Master device should connect to ws://{ip_address}:8765/master")
        logger.info(f"Farm devices should connect to ws://{ip_address}:8765/farm")
    except Exception as e:
        logger.error(f"Could not determine local IP address: {e}")

    # Use websockets router for cleaner path-based routing
    try:
        from websockets.server import serve
        from websockets.routing import Router
        
        # Create router with path-based handlers
        router = Router()
        router.add_route("/master", handle_master_device)
        router.add_route("/farm", handle_farm_device)
        
        # Start server with router
        async with serve(router, server_host, server_port):
            logger.info("Server started with router-based routing")
            await asyncio.Future()  # Run forever
            
    except ImportError:
        # Fallback to manual routing if Router is not available
        logger.info("Router not available, using manual routing")
        
        async def route_handler(websocket):
            """Route connections based on path"""
            # Access path through websocket.request.path (newer websockets library)
            path = getattr(websocket, 'request', None)
            if path and hasattr(path, 'path'):
                path = path.path
            else:
                # Fallback for older versions or if request is not available
                path = getattr(websocket, 'path', '/')
            
            client_address = websocket.remote_address if hasattr(websocket, 'remote_address') else 'Unknown'
            logger.info(f"Client connected: {client_address} (Path: {path})")
            
            if path == "/master":
                await handle_master_device(websocket)
            elif path == "/farm":
                await handle_farm_device(websocket)
            else:
                logger.warning(f"Unknown connection path: {path}")
                await websocket.close(1008, "Invalid path")

        # Start the server with manual path-based routing
        start_server = websockets.serve(route_handler, server_host, server_port)
        server = await start_server
        
        # Keep the server running indefinitely
        await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Server crashed: {e}")