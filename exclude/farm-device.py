async def get_device_info(device_id):
    """Get device information for debugging"""
    try:
        # Get device model
        model_process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getprop', 'ro.product.model',
            stdout=asyncio.subprocess.PIPE
        )
        model_stdout, _ = await model_process.communicate()
        model = model_stdout.decode('utf-8').strip()
        
        # Get Android version
        version_process = await asyncio.create_subprocess_exec(
            'adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release',
            stdout=asyncio.subprocess.PIPE
        )
        version_stdout, _ = await version_process.communicate()
        version = version_stdout.decode('utf-8').strip()
        
        return {
            "id": device_id,
            "model": model,
            "android_version": version
        }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {"id": device_id, "model": "Unknown", "android_version": "Unknown"}

async def handle_messages(websocket):
    """Handle incoming messages from the central server"""
    device_id = await get_device_id()
    if not device_id:
        logger.error("No device ID available. Cannot execute actions.")
        return
    
    # Get and log device information
    device_info = await get_device_info(device_id)
    logger.info(f"Farm device: {device_info['model']} (Android {device_info['android_version']}, ID: {device_info['id']})")
    
    # Send device info to central server for debugging
    try:
        await websocket.send(json.dumps({
            "action": "device_info", 
            "role": "farm", 
            "device_info": device_info
        }))
    except Exception as e:
        logger.error(f"Error sending device info: {e}")
        
    logger.info(f"Listening for actions to execute on device: {device_id}")
    
    # Rest of the function remains the same...