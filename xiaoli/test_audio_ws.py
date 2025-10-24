#!/usr/bin/env python3
"""
Test WebSocket with simple audio data
"""

import asyncio
import websockets
import json
import base64
import numpy as np

async def test_audio_websocket():
    """Test WebSocket with audio data"""
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
            
            # Generate simple test audio (sine wave)
            sample_rate = 16000
            duration = 0.1  # 100ms
            frequency = 440  # Hz
            
            samples = int(sample_rate * duration)
            t = np.linspace(0, duration, samples, False)
            audio_data = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_pcm = (audio_data * 32767).astype(np.int16)
            
            # Convert to base64
            audio_bytes = audio_pcm.tobytes()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            print(f"Generated test audio: {len(audio_bytes)} bytes")
            
            # Send audio data
            audio_msg = {
                "type": "audio_data",
                "audio_data": audio_base64,
                "sample_rate": sample_rate,
                "channels": 1,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(audio_msg))
            print("Sent audio data")
            
            # Wait a bit for processing
            await asyncio.sleep(1)
            
            # Send stop detection
            stop_msg = {"type": "stop_detection"}
            await websocket.send(json.dumps(stop_msg))
            print("Sent stop detection")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received: {response}")
            
            print("✅ Audio WebSocket test completed successfully")
            
    except asyncio.TimeoutError:
        print("❌ WebSocket test timed out")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_audio_websocket())
