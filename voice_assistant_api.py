"""
语音助手WebSocket API
提供实时的语音处理服务
"""
import asyncio
import json
import numpy as np
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from loguru import logger

from backend.core.voice_assistant_pipeline import VoiceAssistantPipeline, PipelineEvent


class VoiceAssistantWebSocketAPI:
    """语音助手WebSocket API"""
    
    def __init__(self):
        self.app = FastAPI(title="语音助手API", version="1.0.0")
        self.pipeline = VoiceAssistantPipeline()
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 设置流水线事件处理
        self.pipeline.add_event_callback(self.on_pipeline_event)
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def get_homepage():
            """返回演示页面"""
            return HTMLResponse(content=self.get_demo_html())
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket端点"""
            await websocket.accept()
            self.active_connections[client_id] = websocket
            
            logger.info(f"客户端 {client_id} 已连接")
            
            try:
                # 发送连接成功消息
                await websocket.send_text(json.dumps({
                    "type": "connected",
                    "message": "连接成功",
                    "client_id": client_id
                }))
                
                # 启动流水线
                await self.pipeline.start_pipeline()
                
                while True:
                    try:
                        # 接收音频数据
                        data = await websocket.receive_bytes()
                        
                        # 将字节数据转换为numpy数组
                        audio_data = np.frombuffer(data, dtype=np.float32)
                        
                        # 添加调试日志
                        logger.debug(f"收到音频数据: {len(audio_data)} 样本, 范围: [{audio_data.min():.3f}, {audio_data.max():.3f}]")
                        
                        # 处理音频数据
                        await self.pipeline.process_audio_chunk(audio_data)
                        
                    except Exception as e:
                        logger.error(f"处理音频数据时出错: {e}")
                        # 继续处理，不中断连接
                    
            except WebSocketDisconnect:
                logger.info(f"客户端 {client_id} 断开连接")
                await self.pipeline.stop_pipeline()
            except Exception as e:
                logger.error(f"WebSocket错误: {e}")
                await websocket.close()
            finally:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]
        
        @self.app.get("/api/status")
        async def get_status():
            """获取流水线状态"""
            return self.pipeline.get_pipeline_status()
        
        @self.app.post("/api/start")
        async def start_pipeline():
            """启动流水线"""
            await self.pipeline.start_pipeline()
            return {"message": "流水线已启动"}
        
        @self.app.post("/api/stop")
        async def stop_pipeline():
            """停止流水线"""
            await self.pipeline.stop_pipeline()
            return {"message": "流水线已停止"}
    
    def on_pipeline_event(self, event: PipelineEvent):
        """处理流水线事件"""
        # 向所有连接的客户端广播事件
        message = {
            "type": "pipeline_event",
            "event_type": event.event_type,
            "data": event.data,
            "state": event.state.value,
            "timestamp": event.timestamp
        }
        
        # 异步发送消息
        asyncio.create_task(self.broadcast_message(message))
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            return
        
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"发送消息到客户端 {client_id} 失败: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            del self.active_connections[client_id]
    
    def get_demo_html(self) -> str:
        """获取演示页面HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>语音助手演示</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-weight: bold;
        }
        .status.listening { background-color: #e3f2fd; color: #1976d2; }
        .status.processing { background-color: #fff3e0; color: #f57c00; }
        .status.speaking { background-color: #e8f5e8; color: #388e3c; }
        .status.idle { background-color: #f3e5f5; color: #7b1fa2; }
        
        .controls {
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            margin: 5px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .start-btn { background-color: #4caf50; color: white; }
        .stop-btn { background-color: #f44336; color: white; }
        .record-btn { background-color: #2196f3; color: white; }
        
        .log {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 10px;
            height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
        }
        
        .log-entry {
            margin: 2px 0;
            padding: 2px 5px;
            border-radius: 3px;
        }
        .log-info { background-color: #e3f2fd; }
        .log-success { background-color: #e8f5e8; }
        .log-warning { background-color: #fff3e0; }
        .log-error { background-color: #ffebee; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 语音助手演示</h1>
        
        <div id="status" class="status idle">
            状态: 空闲
        </div>
        
        <div class="controls">
            <button id="connectBtn" class="start-btn">连接</button>
            <button id="disconnectBtn" class="stop-btn" disabled>断开</button>
            <button id="recordBtn" class="record-btn" disabled>开始录音</button>
        </div>
        
        <div>
            <h3>事件日志</h3>
            <div id="log" class="log"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let mediaRecorder = null;
        let audioContext = null;
        let isRecording = false;
        
        const statusEl = document.getElementById('status');
        const logEl = document.getElementById('log');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const recordBtn = document.getElementById('recordBtn');
        
        function log(message, type = 'info') {
            const entry = document.createElement('div');
            entry.className = `log-entry log-${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logEl.appendChild(entry);
            logEl.scrollTop = logEl.scrollHeight;
        }
        
        function updateStatus(state, message = '') {
            statusEl.className = `status ${state}`;
            statusEl.textContent = `状态: ${message || state}`;
        }
        
        connectBtn.onclick = function() {
            const clientId = 'client_' + Date.now();
            ws = new WebSocket(`ws://192.168.73.130:8000/ws/${clientId}`);
            
            ws.onopen = function() {
                log('WebSocket连接已建立', 'success');
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                recordBtn.disabled = false;
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'connected') {
                    log(`连接成功，客户端ID: ${data.client_id}`, 'success');
                } else if (data.type === 'pipeline_event') {
                    log(`流水线事件: ${data.event_type} - ${data.state}`, 'info');
                    
                    // 更新状态显示
                    switch(data.state) {
                        case 'listening':
                            updateStatus('listening', '监听中...');
                            break;
                        case 'speech_recognition':
                            updateStatus('processing', '语音识别中...');
                            break;
                        case 'intent_processing':
                            updateStatus('processing', '意图识别中...');
                            break;
                        case 'executing_command':
                            updateStatus('processing', '执行指令中...');
                            break;
                        case 'speaking':
                            updateStatus('speaking', '语音合成中...');
                            break;
                        case 'idle':
                            updateStatus('idle', '空闲');
                            break;
                    }
                    
                    // 显示具体信息
                    if (data.event_type === 'wake_word_detected') {
                        log(`🎯 检测到唤醒词: ${data.data.keyword}`, 'success');
                    } else if (data.event_type === 'intent_processing_started') {
                        log(`🧠 识别文本: ${data.data.text}`, 'info');
                    } else if (data.event_type === 'tts_started') {
                        log(`🔊 回复: ${data.data.response}`, 'success');
                    }
                }
            };
            
            ws.onclose = function() {
                log('WebSocket连接已关闭', 'warning');
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                recordBtn.disabled = true;
                updateStatus('idle', '已断开');
            };
            
            ws.onerror = function(error) {
                log(`WebSocket错误: ${error}`, 'error');
            };
        };
        
        disconnectBtn.onclick = function() {
            if (ws) {
                ws.close();
            }
            if (isRecording) {
                stopRecording();
            }
        };
        
        recordBtn.onclick = function() {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        };
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioContext = new AudioContext({ sampleRate: 16000 });
                const source = audioContext.createMediaStreamSource(stream);
                
                // 使用更小的缓冲区大小，提高实时性
                const processor = audioContext.createScriptProcessor(1024, 1, 1);
                processor.onaudioprocess = function(e) {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        const audioData = e.inputBuffer.getChannelData(0);
                        
                        // 检查音频数据是否有效
                        const hasAudio = audioData.some(sample => Math.abs(sample) > 0.001);
                        if (hasAudio) {
                            // 转换为Float32Array并发送
                            const buffer = new Float32Array(audioData);
                            try {
                                ws.send(buffer.buffer);
                            } catch (error) {
                                console.error('发送音频数据失败:', error);
                            }
                        }
                    }
                };
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                
                isRecording = true;
                recordBtn.textContent = '停止录音';
                recordBtn.style.backgroundColor = '#f44336';
                log('开始录音...', 'info');
                
            } catch (error) {
                log(`录音启动失败: ${error}`, 'error');
            }
        }
        
        function stopRecording() {
            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }
            
            isRecording = false;
            recordBtn.textContent = '开始录音';
            recordBtn.style.backgroundColor = '#2196f3';
            log('录音已停止', 'info');
        }
    </script>
</body>
</html>
        """


# 创建API实例
api = VoiceAssistantWebSocketAPI()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api.app, host="0.0.0.0", port=8000)
