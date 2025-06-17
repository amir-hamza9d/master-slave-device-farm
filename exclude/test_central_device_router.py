import unittest
import asyncio
import websockets
import json
import sys
import os
sys.path.append(os.path.abspath('.'))
from unittest.mock import MagicMock
from central_device_router import handle_master_device, handle_farm_device, broadcast_to_farm_devices, farm_devices

class TestCentralDeviceRouter(unittest.TestCase):

    async def test_handle_master_device(self):
        websocket_mock = MagicMock()
        websocket_mock.remote_address = "test_master"
        websocket_mock.recv.return_value = json.dumps({"action": "test_action"})

        await handle_master_device(websocket_mock)

        self.assertEqual(len(farm_devices), 0)

    async def test_handle_farm_device(self):
        websocket_mock = MagicMock()
        websocket_mock.remote_address = "test_farm"
        websocket_mock.recv.return_value = json.dumps({"action": "test_action"})

        await handle_farm_device(websocket_mock)

        self.assertEqual(len(farm_devices), 1)

    async def test_broadcast_to_farm_devices(self):
        websocket_mock = MagicMock()
        websocket_mock.remote_address = "test_farm"
        farm_devices.add(websocket_mock)

        message = json.dumps({"action": "test_action"})
        await broadcast_to_farm_devices(message)

        websocket_mock.send.assert_called_with(message)

if __name__ == '__main__':
    asyncio.run(unittest.main())