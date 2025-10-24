#!/usr/bin/env python3
"""
Test WebSocket with minimal audio processing
"""

import asyncio
import websockets
import json
import base64
import numpy as np

async def test_simple_audio():
    """Test WebSocket with simple audio data"""
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
            
            # Send very small audio data
            audio_data = np.zeros(100, dtype=np.int16)  # Silent audio
            audio_bytes = audio_data.tobytes()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            print(f"Generated silent audio: {len(audio_bytes)} bytes")
            
            # Send audio data
            audio_msg = {
                "type": "audio_data",
                "audio_data": audio_base64,
                "sample_rate": 16000,
                "channels": 1,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(audio_msg))
            print("Sent audio data")
            
            # Wait a bit
            await asyncio.sleep(0.5)
            
            # Send stop detection
            stop_msg = {"type": "stop_detection"}
            await websocket.send(json.dumps(stop_msg))
            print("Sent stop detection")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            print("✅ Simple audio test completed successfully")
            
    except Exception as e:
        print(f"❌ Simple audio test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_audio())
