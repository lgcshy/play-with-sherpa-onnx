#!/usr/bin/env python3
"""
Simple WebSocket test for KWS API
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection"""
    uri = "ws://localhost:8000/ws/kws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send start detection
            start_msg = {"type": "start_detection"}
            await websocket.send(json.dumps(start_msg))
            print("Sent start detection")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            # Send stop detection
            stop_msg = {"type": "stop_detection"}
            await websocket.send(json.dumps(stop_msg))
            print("Sent stop detection")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            print("✅ WebSocket test completed successfully")
            
    except asyncio.TimeoutError:
        print("❌ WebSocket test timed out")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
