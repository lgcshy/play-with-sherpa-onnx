#!/usr/bin/env python3
"""
Test minimal WebSocket server
"""

import asyncio
import websockets
import json
import base64
import numpy as np

async def test_minimal_ws():
    """Test minimal WebSocket server"""
    uri = "ws://localhost:8001/ws/test"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Test ping
            ping_msg = {"type": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print("Sent ping")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            # Test audio data
            audio_data = np.random.randint(-32768, 32767, 1600, dtype=np.int16)
            audio_bytes = audio_data.tobytes()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            audio_msg = {
                "type": "audio_data",
                "audio_data": audio_base64
            }
            
            await websocket.send(json.dumps(audio_msg))
            print("Sent audio data")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            print("✅ Minimal WebSocket test completed successfully")
            
    except Exception as e:
        print(f"❌ Minimal WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_minimal_ws())
