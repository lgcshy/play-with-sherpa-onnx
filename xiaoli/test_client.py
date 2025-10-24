#!/usr/bin/env python3
"""
Test client for Xiaoli KWS WebSocket API
Tests PCM audio streaming functionality
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import wave
import os
from typing import Optional

class KWSClient:
    """Test client for KWS WebSocket API"""
    
    def __init__(self, uri: str = "ws://localhost:8000/ws/kws"):
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            print(f"Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("Disconnected from server")
    
    async def send_audio_data(self, audio_data: bytes):
        """Send PCM audio data to server"""
        if not self.is_connected or not self.websocket:
            print("Not connected to server")
            return
        
        try:
            # Encode audio data as base64
            base64_audio = base64.b64encode(audio_data).decode('utf-8')
            
            # Create message
            message = {
                "type": "audio_data",
                "audio_data": base64_audio,
                "sample_rate": 16000,
                "channels": 1,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send message
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            print(f"Error sending audio data: {e}")
    
    async def start_detection(self):
        """Send start detection command"""
        if not self.is_connected or not self.websocket:
            print("Not connected to server")
            return
        
        try:
            message = {"type": "start_detection"}
            await self.websocket.send(json.dumps(message))
            print("Detection started")
        except Exception as e:
            print(f"Error starting detection: {e}")
    
    async def stop_detection(self):
        """Send stop detection command"""
        if not self.is_connected or not self.websocket:
            print("Not connected to server")
            return
        
        try:
            message = {"type": "stop_detection"}
            await self.websocket.send(json.dumps(message))
            print("Detection stopped")
        except Exception as e:
            print(f"Error stopping detection: {e}")
    
    async def listen_for_responses(self):
        """Listen for server responses"""
        if not self.is_connected or not self.websocket:
            print("Not connected to server")
            return
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data.get("type") == "detection":
                    print(f"🎯 Keyword detected: {data['keyword']} (confidence: {data['confidence']:.3f})")
                elif data.get("type") == "detection_started":
                    print("✅ Detection started")
                elif data.get("type") == "detection_stopped":
                    print("⏹️ Detection stopped")
                elif data.get("type") == "error":
                    print(f"❌ Error: {data['message']}")
                else:
                    print(f"📨 Received: {data}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
        except Exception as e:
            print(f"Error listening for responses: {e}")

def load_test_audio(file_path: str) -> bytes:
    """Load test audio file"""
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # Check if file is compatible
            if wav_file.getnchannels() != 1:
                print(f"Warning: Audio file has {wav_file.getnchannels()} channels, expected 1")
            if wav_file.getframerate() != 16000:
                print(f"Warning: Audio file has {wav_file.getframerate()} Hz sample rate, expected 16000")
            
            # Read audio data
            audio_data = wav_file.readframes(wav_file.getnframes())
            print(f"Loaded audio file: {file_path}")
            print(f"Duration: {wav_file.getnframes() / wav_file.getframerate():.2f} seconds")
            print(f"Sample rate: {wav_file.getframerate()} Hz")
            print(f"Channels: {wav_file.getnchannels()}")
            print(f"Sample width: {wav_file.getsampwidth()} bytes")
            
            return audio_data
            
    except Exception as e:
        print(f"Error loading audio file: {e}")
        return b""

def generate_sine_wave(frequency: float = 440.0, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate a sine wave for testing"""
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples, False)
    wave_data = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    return wave_data.tobytes()

async def test_with_audio_file(client: KWSClient, audio_file: str):
    """Test with audio file"""
    print(f"\n🎵 Testing with audio file: {audio_file}")
    
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        return
    
    # Load audio data
    audio_data = load_test_audio(audio_file)
    if not audio_data:
        return
    
    # Start detection
    await client.start_detection()
    
    # Send audio data in chunks
    chunk_size = 1600  # 100ms at 16kHz
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        await client.send_audio_data(chunk)
        await asyncio.sleep(0.1)  # 100ms delay between chunks
    
    # Stop detection
    await client.stop_detection()

async def test_with_sine_wave(client: KWSClient):
    """Test with generated sine wave"""
    print("\n🔊 Testing with sine wave")
    
    # Start detection
    await client.start_detection()
    
    # Generate and send sine wave
    sine_data = generate_sine_wave(frequency=440.0, duration=2.0)
    chunk_size = 1600  # 100ms at 16kHz
    
    for i in range(0, len(sine_data), chunk_size):
        chunk = sine_data[i:i + chunk_size]
        await client.send_audio_data(chunk)
        await asyncio.sleep(0.1)  # 100ms delay between chunks
    
    # Stop detection
    await client.stop_detection()

async def main():
    """Main test function"""
    print("Xiaoli KWS WebSocket Test Client")
    print("=" * 40)
    
    # Create client
    client = KWSClient()
    
    # Connect to server
    if not await client.connect():
        return
    
    try:
        # Start listening for responses in background
        listen_task = asyncio.create_task(client.listen_for_responses())
        
        # Test with sine wave
        await test_with_sine_wave(client)
        
        # Test with audio files if available
        test_files = [
            "xiaoli/model_data/kws/test_wavs/0.wav",
            "xiaoli/model_data/kws/test_wavs/1.wav",
            "xiaoli/model_data/kws/test_wavs/2.wav"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                await test_with_audio_file(client, test_file)
                await asyncio.sleep(1)  # Wait between tests
        
        # Wait a bit for any remaining responses
        await asyncio.sleep(2)
        
        # Cancel listen task
        listen_task.cancel()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
