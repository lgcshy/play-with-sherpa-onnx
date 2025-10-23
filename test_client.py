#!/usr/bin/env python3
"""
WebSocket客户端测试脚本
"""
import asyncio
import websockets
import json
import numpy as np
import wave
import sys
from pathlib import Path


async def test_websocket():
    """测试WebSocket连接和音频传输"""
    uri = "ws://192.168.73.130:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")
            
            # 接收连接确认消息
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 收到消息: {data}")
            
            # 发送测试音频数据（静音）
            print("🎤 发送测试音频数据...")
            for i in range(10):  # 发送10个音频块
                # 创建静音数据
                audio_data = np.zeros(1600, dtype=np.int16)  # 100ms的静音
                await websocket.send(audio_data.tobytes())
                await asyncio.sleep(0.1)  # 100ms间隔
            
            print("✅ 测试完成")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_with_audio_file():
    """使用音频文件测试"""
    uri = "ws://192.168.73.130:8000/ws"
    audio_file = Path("models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/test_wavs/1.wav")
    
    if not audio_file.exists():
        print(f"❌ 音频文件不存在: {audio_file}")
        return
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")
            
            # 接收连接确认消息
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 收到消息: {data}")
            
            # 读取音频文件
            with wave.open(str(audio_file), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                
                print(f"📊 音频信息: 采样率={sample_rate}, 声道={channels}, 位深={sample_width}")
                
                # 读取音频数据
                frames = wav_file.readframes(wav_file.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # 分块发送
                chunk_size = 1600  # 100ms chunks
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i+chunk_size]
                    if len(chunk) < chunk_size:
                        # 填充不足的块
                        chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
                    
                    await websocket.send(chunk.tobytes())
                    await asyncio.sleep(0.1)  # 100ms间隔
                    
                    # 检查是否有检测结果
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                        data = json.loads(message)
                        if data.get('type') == 'keyword_detected':
                            print(f"🎯 检测到唤醒词: {data.get('keyword')}")
                    except asyncio.TimeoutError:
                        pass  # 没有消息是正常的
            
            print("✅ 音频文件测试完成")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "file":
        asyncio.run(test_with_audio_file())
    else:
        asyncio.run(test_websocket())
