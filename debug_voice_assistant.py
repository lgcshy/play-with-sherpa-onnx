#!/usr/bin/env python3
"""
语音助手调试版本
添加详细的调试信息来诊断问题
"""
import asyncio
import json
import numpy as np
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from loguru import logger

from backend.core.voice_assistant_pipeline import VoiceAssistantPipeline, PipelineEvent


class DebugVoiceAssistantAPI:
    """调试版语音助手WebSocket API"""
    
    def __init__(self):
        self.app = FastAPI(title="语音助手调试API", version="1.0.0")
        self.pipeline = VoiceAssistantPipeline()
        self.active_connections: Dict[str, WebSocket] = {}
        self.audio_chunk_count = 0
        
        # 设置流水线事件处理
        self.pipeline.add_event_callback(self.on_pipeline_event)
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/")
        async def get_homepage():
            """返回调试页面"""
            return HTMLResponse(content=self.get_debug_html())
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket端点"""
            await websocket.accept()
            self.active_connections[client_id] = websocket
            
            logger.info(f"🔗 客户端 {client_id} 已连接")
            
            try:
                # 发送连接成功消息
                await websocket.send_text(json.dumps({
                    "type": "connected",
                    "message": "连接成功",
                    "client_id": client_id
                }))
                
                # 启动流水线
                await self.pipeline.start_pipeline()
                logger.info("🚀 流水线已启动")
                
                while True:
                    try:
                        # 接收数据 - 尝试接收字节数据
                        logger.info("⏳ 等待接收数据...")
                        try:
                            # 尝试接收字节数据
                            data = await websocket.receive_bytes()
                            self.audio_chunk_count += 1
                            logger.info(f"📥 收到音频数据: {len(data)} 字节")
                        except Exception as receive_error:
                            logger.error(f"❌ 接收字节数据失败: {receive_error}")
                            # 尝试接收文本数据
                            try:
                                text_data = await websocket.receive_text()
                                logger.info(f"📥 收到文本数据: {text_data}")
                                continue
                            except Exception as text_error:
                                logger.error(f"❌ 接收文本数据也失败: {text_error}")
                                import traceback
                                logger.error(f"❌ 接收错误详情: {traceback.format_exc()}")
                                continue
                        
                        # 将字节数据转换为numpy数组
                        audio_data = np.frombuffer(data, dtype=np.float32)
                        
                        # 详细的调试日志 - 减少日志频率
                        if self.audio_chunk_count % 10 == 0:  # 每10个音频块才输出一次
                            logger.info(f"📊 音频块 #{self.audio_chunk_count}: {len(audio_data)} 样本")
                            logger.info(f"📊 音频范围: [{audio_data.min():.6f}, {audio_data.max():.6f}]")
                            logger.info(f"📊 音频RMS: {np.sqrt(np.mean(audio_data**2)):.6f}")
                            
                            # 检查音频数据是否有效
                            if np.abs(audio_data).max() < 0.001:
                                logger.warning("⚠️ 音频数据几乎为静音")
                            else:
                                logger.info("✅ 检测到有效音频数据")
                        
                        # 处理音频数据
                        try:
                            await self.pipeline.process_audio_chunk(audio_data)
                        except Exception as pipeline_error:
                            logger.error(f"❌ 流水线处理错误: {pipeline_error}")
                            import traceback
                            logger.error(f"❌ 流水线错误详情: {traceback.format_exc()}")
                            # 继续处理，不中断连接
                        
                        # 每10个音频块发送一次状态更新
                        if self.audio_chunk_count % 10 == 0:
                            try:
                                await websocket.send_text(json.dumps({
                                    "type": "status_update",
                                    "audio_chunks_processed": self.audio_chunk_count,
                                    "pipeline_state": self.pipeline.state.value
                                }))
                            except Exception as send_error:
                                logger.error(f"❌ 发送状态更新失败: {send_error}")
                        
                    except Exception as e:
                        logger.error(f"❌ 处理音频数据时出错: {e}")
                        # 继续处理，不中断连接
                    
            except WebSocketDisconnect:
                logger.info(f"🔌 客户端 {client_id} 断开连接")
                await self.pipeline.stop_pipeline()
            except Exception as e:
                logger.error(f"❌ WebSocket错误: {e}")
                await websocket.close()
            finally:
                if client_id in self.active_connections:
                    del self.active_connections[client_id]
        
        @self.app.get("/api/debug/status")
        async def get_debug_status():
            """获取详细调试状态"""
            return {
                "pipeline_status": self.pipeline.get_pipeline_status(),
                "active_connections": len(self.active_connections),
                "audio_chunks_processed": self.audio_chunk_count,
                "connections": list(self.active_connections.keys())
            }
    
    def on_pipeline_event(self, event: PipelineEvent):
        """处理流水线事件"""
        logger.info(f"📢 流水线事件: {event.event_type} - 状态: {event.state.value}")
        
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
                logger.error(f"❌ 发送消息到客户端 {client_id} 失败: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            del self.active_connections[client_id]
    
    def get_debug_html(self) -> str:
        """获取调试页面HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>语音助手调试页面</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
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
            height: 400px;
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
        .log-debug { background-color: #f3e5f5; }
        
        .stats {
            display: flex;
            gap: 20px;
            margin: 10px 0;
        }
        .stat-item {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #1976d2;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 语音助手调试页面</h1>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="audioChunks">0</div>
                <div class="stat-label">音频块</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="connectionStatus">断开</div>
                <div class="stat-label">连接状态</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="pipelineState">idle</div>
                <div class="stat-label">流水线状态</div>
            </div>
        </div>
        
        <div id="status" class="status idle">
            状态: 空闲
        </div>
        
        <div class="controls">
            <button id="connectBtn" class="start-btn">连接</button>
            <button id="disconnectBtn" class="stop-btn" disabled>断开</button>
            <button id="recordBtn" class="record-btn" disabled>开始录音</button>
            <button id="testBtn" class="record-btn" disabled>测试音频</button>
        </div>
        
        <div>
            <h3>调试日志</h3>
            <div id="log" class="log"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let audioContext = null;
        let isRecording = false;
        let audioChunkCount = 0;
        
        const statusEl = document.getElementById('status');
        const logEl = document.getElementById('log');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const recordBtn = document.getElementById('recordBtn');
        const testBtn = document.getElementById('testBtn');
        const audioChunksEl = document.getElementById('audioChunks');
        const connectionStatusEl = document.getElementById('connectionStatus');
        const pipelineStateEl = document.getElementById('pipelineState');
        
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
            pipelineStateEl.textContent = state;
        }
        
        function updateStats() {
            audioChunksEl.textContent = audioChunkCount;
        }
        
        connectBtn.onclick = function() {
            const clientId = 'debug_client_' + Date.now();
            ws = new WebSocket(`ws://192.168.73.130:8000/ws/${clientId}`);
            
            ws.onopen = function() {
                log('WebSocket连接已建立', 'success');
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                recordBtn.disabled = false;
                testBtn.disabled = false;
                connectionStatusEl.textContent = '已连接';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'connected') {
                    log(`连接成功，客户端ID: ${data.client_id}`, 'success');
                } else if (data.type === 'status_update') {
                    audioChunkCount = data.audio_chunks_processed;
                    updateStats();
                    log(`状态更新: 已处理 ${data.audio_chunks_processed} 个音频块`, 'debug');
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
                testBtn.disabled = true;
                updateStatus('idle', '已断开');
                connectionStatusEl.textContent = '断开';
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
        
        testBtn.onclick = function() {
            testAudioGeneration();
        };
        
        async function startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioContext = new AudioContext({ sampleRate: 16000 });
                const source = audioContext.createMediaStreamSource(stream);
                
                const processor = audioContext.createScriptProcessor(1024, 1, 1);
                processor.onaudioprocess = function(e) {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        const audioData = e.inputBuffer.getChannelData(0);
                        
                        // 检查音频数据是否有效
                        const hasAudio = audioData.some(sample => Math.abs(sample) > 0.001);
                        if (hasAudio) {
                            const buffer = new Float32Array(audioData);
                            try {
                                ws.send(buffer.buffer);
                                audioChunkCount++;
                                updateStats();
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
        
        function testAudioGeneration() {
            log('开始测试音频生成...', 'info');
            
            // 生成测试音频数据
            const sampleRate = 16000;
            const duration = 1.0; // 1秒
            const samples = sampleRate * duration;
            
            // 生成正弦波测试音频
            const testAudio = new Float32Array(samples);
            for (let i = 0; i < samples; i++) {
                testAudio[i] = 0.1 * Math.sin(2 * Math.PI * 440 * i / sampleRate); // 440Hz正弦波
            }
            
            // 分块发送
            const chunkSize = 1024;
            for (let i = 0; i < samples; i += chunkSize) {
                const chunk = testAudio.slice(i, i + chunkSize);
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(chunk.buffer);
                    audioChunkCount++;
                }
            }
            
            updateStats();
            log(`测试音频已发送: ${samples} 样本`, 'success');
        }
    </script>
</body>
</html>
        """


# 创建调试API实例
debug_api = DebugVoiceAssistantAPI()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(debug_api.app, host="0.0.0.0", port=8000)
