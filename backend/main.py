"""
FastAPI WebSocket 服务器
"""
import asyncio
import json
import numpy as np
import time
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger
import uvicorn

from .config import HOST, PORT, DEBUG, SAMPLE_RATE, CHUNK_SIZE
from .core import KeywordSpotter


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.spotter_instances: Dict[str, KeywordSpotter] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # 为每个连接创建独立的关键词检测器实例
        try:
            spotter = KeywordSpotter()
            spotter.reset_vad()  # 重置VAD状态
            self.spotter_instances[client_id] = spotter
            logger.info(f"客户端 {client_id} 连接成功，检测器初始化完成")
        except Exception as e:
            logger.error(f"客户端 {client_id} 检测器初始化失败: {e}")
            await websocket.close(code=1011, reason="检测器初始化失败")
            return False
        
        return True
    
    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.spotter_instances:
            del self.spotter_instances[client_id]
        logger.info(f"客户端 {client_id} 断开连接")
    
    async def send_message(self, client_id: str, message: dict):
        """发送消息给指定客户端"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送消息失败 {client_id}: {e}")
                self.disconnect(client_id)


# 创建FastAPI应用
app = FastAPI(
    title="Sherpa-ONNX 唤醒词检测系统",
    description="基于Sherpa-ONNX的中文唤醒词实时检测系统",
    version="0.1.0"
)

# 连接管理器
manager = ConnectionManager()

# 音频流存储
audio_streams: Dict[str, any] = {}


@app.get("/")
async def root():
    """根路径，返回简单的HTML页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sherpa-ONNX 唤醒词检测</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .detected { background-color: #fff3cd; color: #856404; }
            button { padding: 10px 20px; margin: 5px; font-size: 16px; }
            #log { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Sherpa-ONNX 唤醒词检测系统</h1>
            <div id="status" class="status disconnected">未连接</div>
            <button id="connectBtn">连接</button>
            <button id="startBtn" disabled>开始录音</button>
            <button id="stopBtn" disabled>停止录音</button>
            <h3>检测日志:</h3>
            <div id="log"></div>
        </div>
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioContext = null;
            let isRecording = false;
            
            const statusDiv = document.getElementById('status');
            const connectBtn = document.getElementById('connectBtn');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const logDiv = document.getElementById('log');
            
            function log(message) {
                const time = new Date().toLocaleTimeString();
                logDiv.innerHTML += `[${time}] ${message}<br>`;
                logDiv.scrollTop = logDiv.scrollHeight;
            }
            
            function updateStatus(message, className) {
                statusDiv.textContent = message;
                statusDiv.className = `status ${className}`;
            }
            
            connectBtn.onclick = function() {
                if (ws) {
                    ws.close();
                }
                
                ws = new WebSocket('ws://192.168.73.130:8000/ws');
                
                ws.onopen = function() {
                    updateStatus('已连接', 'connected');
                    connectBtn.textContent = '断开';
                    startBtn.disabled = false;
                    log('WebSocket连接已建立');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'keyword_detected') {
                        const latency = data.latency_ms ? ` (延迟: ${data.latency_ms.toFixed(1)}ms)` : '';
                        log(`🎯 检测到唤醒词: ${data.keyword}${latency}`);
                        updateStatus(`检测到: ${data.keyword}`, 'detected');
                    } else if (data.type === 'error') {
                        log(`❌ 错误: ${data.message}`);
                    }
                };
                
                ws.onclose = function() {
                    updateStatus('连接断开', 'disconnected');
                    connectBtn.textContent = '连接';
                    startBtn.disabled = true;
                    stopBtn.disabled = true;
                    log('WebSocket连接已断开');
                };
                
                ws.onerror = function(error) {
                    log(`❌ WebSocket错误: ${error}`);
                };
            };
            
            startBtn.onclick = async function() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioContext = new AudioContext({ sampleRate: 16000 });
                    const source = audioContext.createMediaStreamSource(stream);
                    
                    const processor = audioContext.createScriptProcessor(4096, 1, 1);
                    processor.onaudioprocess = function(e) {
                        if (isRecording && ws && ws.readyState === WebSocket.OPEN) {
                            const inputData = e.inputBuffer.getChannelData(0);
                            const pcmData = new Int16Array(inputData.length);
                            for (let i = 0; i < inputData.length; i++) {
                                pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                            }
                            
                            // 使用JSON格式发送时间戳和音频数据
                            const timestamp = Date.now();
                            const message = {
                                timestamp: timestamp,
                                audioData: Array.from(pcmData)  // 转换为普通数组
                            };
                            
                            ws.send(JSON.stringify(message));
                        }
                    };
                    
                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    
                    isRecording = true;
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    log('开始录音...');
                    
                } catch (error) {
                    log(`❌ 录音启动失败: ${error}`);
                }
            };
            
            stopBtn.onclick = function() {
                isRecording = false;
                if (audioContext) {
                    audioContext.close();
                    audioContext = null;
                }
                startBtn.disabled = false;
                stopBtn.disabled = true;
                log('停止录音');
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/status")
async def get_status():
    """获取服务器状态"""
    return {
        "status": "running",
        "active_connections": len(manager.active_connections),
        "sample_rate": SAMPLE_RATE,
        "chunk_size": CHUNK_SIZE
    }


@app.get("/api/model-info")
async def get_model_info():
    """获取模型信息"""
    try:
        spotter = KeywordSpotter()
        return spotter.get_model_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    client_id = f"client_{len(manager.active_connections)}"
    
    # 建立连接
    if not await manager.connect(websocket, client_id):
        return
    
    try:
        # 初始化音频流
        spotter = manager.spotter_instances[client_id]
        audio_stream = spotter.create_stream()
        audio_streams[client_id] = audio_stream
        
        # 发送连接成功消息
        await manager.send_message(client_id, {
            "type": "connected",
            "client_id": client_id,
            "message": "连接成功"
        })
        
        # 处理音频数据
        logger.info(f"🎤 客户端 {client_id} 开始接收音频数据")
        chunk_count = 0
        while True:
            try:
                # 接收JSON格式的音频数据
                message = await websocket.receive_text()
                data = json.loads(message)
                chunk_count += 1
                
                # 解析时间戳和音频数据
                frontend_timestamp = data['timestamp']
                audio_array = data['audioData']
                
                # 将音频数据转换为numpy数组
                audio_data = np.array(audio_array, dtype=np.int16)
                audio_data = audio_data.astype(np.float32) / 32768.0
                
                # 处理音频数据
                keyword = spotter.process_audio_chunk(audio_stream, audio_data, SAMPLE_RATE)
                
                if keyword:
                    # 计算延迟时间
                    backend_timestamp = time.time() * 1000  # 转换为毫秒
                    latency_ms = backend_timestamp - frontend_timestamp
                    
                    logger.info(f"🎯 客户端 {client_id} 检测到唤醒词: {keyword} (延迟: {latency_ms:.1f}ms)")
                    
                    # 发送检测结果
                    await manager.send_message(client_id, {
                        "type": "keyword_detected",
                        "keyword": keyword,
                        "timestamp": asyncio.get_event_loop().time(),
                        "latency_ms": latency_ms,
                        "frontend_timestamp": frontend_timestamp,
                        "backend_timestamp": backend_timestamp
                    })
                # 只在检测到唤醒词时才打印日志，减少噪音
                
            except WebSocketDisconnect:
                logger.info(f"🔌 客户端 {client_id} WebSocket断开连接")
                break
            except Exception as e:
                logger.error(f"❌ 处理音频数据错误 {client_id}: {e}")
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": f"处理音频数据错误: {e}"
                })
    
    except Exception as e:
        logger.error(f"WebSocket连接错误 {client_id}: {e}")
    finally:
        # 清理资源
        manager.disconnect(client_id)
        if client_id in audio_streams:
            del audio_streams[client_id]


def run_server():
    """运行服务器"""
    logger.info(f"🚀 启动服务器: http://{HOST}:{PORT}")
    logger.info(f"📊 调试模式: {DEBUG}")
    
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
