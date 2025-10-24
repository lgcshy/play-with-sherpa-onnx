# 语音助手流水线系统

## 概述

这是一个完整的语音助手流水线系统，实现了从音频输入到指令执行的完整流程：

```
VAD (语音活动检测) → KWS (关键词检测) → ASR (语音识别) → 意图识别 → 指令执行 → TTS (语音合成)
```

## 系统架构

### 核心组件

1. **VAD (Voice Activity Detection)**
   - 使用Silero VAD v4模型
   - 实时检测语音活动
   - 过滤静音和噪声

2. **KWS (Keyword Spotting)**
   - 使用Sherpa-ONNX关键词检测
   - 支持自定义唤醒词
   - 中文音素转换

3. **ASR (Automatic Speech Recognition)**
   - 占位符实现，可替换为实际ASR服务
   - 支持流式语音识别

4. **意图识别**
   - 基于关键词匹配的简单实现
   - 可扩展为深度学习模型

5. **指令执行**
   - 模块化的指令处理器
   - 支持多种指令类型

6. **TTS (Text-to-Speech)**
   - 占位符实现，可替换为实际TTS服务

### 流水线状态

```python
class PipelineState(Enum):
    IDLE = "idle"                    # 空闲状态
    LISTENING = "listening"          # 监听状态（VAD检测）
    WAKE_WORD_DETECTED = "wake_word_detected"  # 唤醒词检测到
    SPEECH_RECOGNITION = "speech_recognition"  # 语音识别中
    INTENT_PROCESSING = "intent_processing"    # 意图处理中
    EXECUTING_COMMAND = "executing_command"    # 执行指令中
    SPEAKING = "speaking"            # 语音合成播放中
```

## 使用方法

### 1. 基本使用

```python
from backend.core.voice_assistant_pipeline import VoiceAssistantPipeline

# 创建流水线
pipeline = VoiceAssistantPipeline()

# 添加事件回调
def on_event(event):
    print(f"事件: {event.event_type}, 状态: {event.state.value}")

pipeline.add_event_callback(on_event)

# 启动流水线
await pipeline.start_pipeline()

# 处理音频数据
audio_data = np.array([...], dtype=np.float32)
await pipeline.process_audio_chunk(audio_data)

# 停止流水线
await pipeline.stop_pipeline()
```

### 2. 运行演示

```bash
# 运行控制台演示
uv run python demo_voice_pipeline.py

# 运行WebSocket API演示
uv run python voice_assistant_api.py
```

然后访问 `http://192.168.73.130:8000` 查看Web界面。

### 3. WebSocket API

```javascript
// 连接WebSocket
const ws = new WebSocket('ws://192.168.73.130:8000/ws/client_123');

// 发送音频数据
const audioData = new Float32Array([...]);
ws.send(audioData.buffer);

// 接收事件
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('流水线事件:', data);
};
```

## 配置说明

### VAD配置

```python
silero_config = sherpa_onnx.SileroVadModelConfig(
    model="path/to/silero_vad.onnx",
    threshold=0.5,                    # 检测阈值
    min_silence_duration=0.5,        # 最小静音时间
    min_speech_duration=0.25,        # 最小语音时间
    window_size=512,                 # 窗口大小
    max_speech_duration=30.0         # 最大语音时间
)
```

### KWS配置

```python
kws = sherpa_onnx.KeywordSpotter(
    tokens="path/to/tokens.txt",
    encoder="path/to/encoder.onnx",
    decoder="path/to/decoder.onnx",
    joiner="path/to/joiner.onnx",
    keywords_file="path/to/keywords.txt",
    keywords_threshold=0.25
)
```

## 扩展指南

### 1. 替换ASR模块

```python
class CustomASRModule:
    async def start_recognition(self) -> str:
        # 实现您的ASR逻辑
        return "识别结果"

# 在VoiceAssistantPipeline中替换
self.asr = CustomASRModule()
```

### 2. 添加新的意图类型

```python
class IntentModule:
    def __init__(self):
        self.intent_patterns = {
            "weather": ["天气", "温度"],
            "music": ["播放", "音乐"],
            "your_intent": ["关键词1", "关键词2"]  # 添加新意图
        }
```

### 3. 添加新的指令处理器

```python
class CommandExecutor:
    def __init__(self):
        self.command_handlers = {
            "your_intent": self._handle_your_intent  # 添加新处理器
        }
    
    async def _handle_your_intent(self, intent_result):
        # 实现您的指令逻辑
        return {"success": True, "response": "处理完成"}
```

## 性能优化

### 1. 音频缓冲

```python
# 使用音频缓冲减少处理延迟
class AudioBuffer:
    def __init__(self, buffer_size=1600):
        self.buffer = []
        self.buffer_size = buffer_size
    
    def add_chunk(self, audio_chunk):
        self.buffer.extend(audio_chunk)
        if len(self.buffer) >= self.buffer_size:
            return self.buffer[:self.buffer_size]
        return None
```

### 2. 异步处理

```python
# 使用异步处理提高并发性能
async def process_audio_async(self, audio_data):
    tasks = [
        self.vad.process_audio_chunk(audio_data),
        self.kws.process_audio_chunk(audio_data)
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## 故障排除

### 1. 模型加载失败

- 检查模型文件路径
- 确认模型文件完整性
- 检查依赖库版本

### 2. 音频处理异常

- 确认音频格式（16kHz, 单声道, float32）
- 检查音频数据范围
- 验证采样率设置

### 3. WebSocket连接问题

- 检查端口是否被占用
- 确认防火墙设置
- 验证客户端音频权限

## 依赖要求

```bash
# 使用uv安装依赖
uv add sherpa-onnx numpy loguru fastapi uvicorn websockets pypinyin
```

## 许可证

本项目基于MIT许可证开源。
