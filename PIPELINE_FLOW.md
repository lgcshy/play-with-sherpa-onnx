# 语音助手流水线流程图

```
音频输入 (PCM数据)
        ↓
    ┌─────────┐
    │   VAD   │ ← 语音活动检测 (Silero VAD v4)
    │ 检测器  │
    └─────────┘
        ↓ (检测到语音)
    ┌─────────┐
    │   KWS   │ ← 关键词检测 (Sherpa-ONNX)
    │ 检测器  │
    └─────────┘
        ↓ (检测到唤醒词)
    ┌─────────┐
    │   ASR   │ ← 语音识别 (占位符实现)
    │ 识别器  │
    └─────────┘
        ↓ (识别文本)
    ┌─────────┐
    │ 意图识别│ ← 意图分析 (关键词匹配)
    │ 处理器  │
    └─────────┘
        ↓ (识别意图)
    ┌─────────┐
    │ 指令执行│ ← 执行指令 (模块化处理器)
    │ 处理器  │
    └─────────┘
        ↓ (执行结果)
    ┌─────────┐
    │   TTS   │ ← 语音合成 (占位符实现)
    │ 合成器  │
    └─────────┘
        ↓
    音频输出 (回复语音)
```

## 状态转换图

```
IDLE (空闲)
  ↓ start_pipeline()
LISTENING (监听)
  ↓ VAD检测到语音 + KWS检测到唤醒词
WAKE_WORD_DETECTED (唤醒词检测到)
  ↓ 进入语音识别
SPEECH_RECOGNITION (语音识别中)
  ↓ 识别完成
INTENT_PROCESSING (意图处理中)
  ↓ 意图识别完成
EXECUTING_COMMAND (执行指令中)
  ↓ 指令执行完成
SPEAKING (语音合成中)
  ↓ TTS完成
LISTENING (返回监听) ← 循环
```

## 事件流

```
1. pipeline_started → 流水线启动
2. wake_word_detected → 检测到唤醒词
3. speech_recognition_started → 开始语音识别
4. intent_processing_started → 开始意图识别
5. command_execution_started → 开始执行指令
6. tts_started → 开始语音合成
7. returned_to_listening → 返回监听状态
8. pipeline_stopped → 流水线停止
```

## 数据流

```
音频数据 (numpy.float32) 
  → VAD处理 (bool: 是否有语音)
  → KWS处理 (str: 检测到的关键词)
  → ASR处理 (str: 识别的文本)
  → 意图识别 (dict: 意图和实体)
  → 指令执行 (dict: 执行结果)
  → TTS处理 (str: 合成的语音)
```

## 异步处理

所有模块都支持异步处理，确保：
- 非阻塞的音频处理
- 并发的事件处理
- 实时的状态更新
- 流畅的用户体验
