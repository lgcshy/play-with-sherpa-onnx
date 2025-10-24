"""
语音助手流水线管理器
实现完整的语音处理流程：VAD -> KWS -> ASR -> 意图识别 -> 执行指令 -> TTS
"""
import asyncio
import numpy as np
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from loguru import logger
import time

from .vad_detector import SileroVAD
from .keyword_spotter import KeywordSpotter


class PipelineState(Enum):
    """流水线状态"""
    IDLE = "idle"                    # 空闲状态
    LISTENING = "listening"          # 监听状态（VAD检测）
    WAKE_WORD_DETECTED = "wake_word_detected"  # 唤醒词检测到
    SPEECH_RECOGNITION = "speech_recognition"  # 语音识别中
    INTENT_PROCESSING = "intent_processing"    # 意图处理中
    EXECUTING_COMMAND = "executing_command"    # 执行指令中
    SPEAKING = "speaking"            # 语音合成播放中


@dataclass
class PipelineEvent:
    """流水线事件"""
    event_type: str
    data: Any
    timestamp: float
    state: PipelineState


class ASRModule:
    """语音识别模块（占位符实现）"""
    
    def __init__(self):
        self.is_processing = False
        self.current_text = ""
    
    async def start_recognition(self) -> str:
        """开始语音识别"""
        logger.info("🎤 开始语音识别...")
        self.is_processing = True
        self.current_text = ""
        
        # 模拟语音识别过程
        await asyncio.sleep(2.0)  # 模拟识别时间
        
        # 模拟识别结果
        sample_texts = [
            "今天天气怎么样",
            "播放音乐",
            "设置闹钟",
            "打开灯",
            "关闭空调"
        ]
        self.current_text = np.random.choice(sample_texts)
        
        logger.info(f"🎤 语音识别结果: {self.current_text}")
        self.is_processing = False
        return self.current_text
    
    def stop_recognition(self):
        """停止语音识别"""
        self.is_processing = False
        logger.info("🎤 语音识别已停止")


class IntentModule:
    """意图识别模块（占位符实现）"""
    
    def __init__(self):
        self.intent_patterns = {
            "weather": ["天气", "温度", "下雨", "晴天"],
            "music": ["播放", "音乐", "歌曲", "听歌"],
            "alarm": ["闹钟", "提醒", "定时"],
            "smart_home": ["开灯", "关灯", "空调", "风扇"],
            "general": ["你好", "谢谢", "再见"]
        }
    
    async def recognize_intent(self, text: str) -> Dict[str, Any]:
        """识别意图"""
        logger.info(f"🧠 意图识别: {text}")
        
        # 简单的关键词匹配
        intent = "general"
        confidence = 0.5
        
        for intent_type, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    intent = intent_type
                    confidence = 0.9
                    break
        
        result = {
            "intent": intent,
            "confidence": confidence,
            "text": text,
            "entities": self._extract_entities(text)
        }
        
        logger.info(f"🧠 意图识别结果: {result}")
        return result
    
    def _extract_entities(self, text: str) -> Dict[str, str]:
        """提取实体"""
        entities = {}
        
        # 简单的时间提取
        if "点" in text or "时" in text:
            entities["time"] = "提取的时间"
        
        # 简单的设备提取
        devices = ["灯", "空调", "风扇", "电视"]
        for device in devices:
            if device in text:
                entities["device"] = device
                break
        
        return entities


class CommandExecutor:
    """指令执行模块（占位符实现）"""
    
    def __init__(self):
        self.command_handlers = {
            "weather": self._handle_weather,
            "music": self._handle_music,
            "alarm": self._handle_alarm,
            "smart_home": self._handle_smart_home,
            "general": self._handle_general
        }
    
    async def execute_command(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行指令"""
        intent = intent_result["intent"]
        text = intent_result["text"]
        
        logger.info(f"⚡ 执行指令: {intent} - {text}")
        
        handler = self.command_handlers.get(intent, self._handle_general)
        result = await handler(intent_result)
        
        logger.info(f"⚡ 指令执行完成: {result}")
        return result
    
    async def _handle_weather(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理天气查询"""
        await asyncio.sleep(1.0)  # 模拟API调用
        return {
            "success": True,
            "response": "今天天气晴朗，温度25度",
            "action": "weather_query"
        }
    
    async def _handle_music(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理音乐播放"""
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "response": "正在播放音乐",
            "action": "play_music"
        }
    
    async def _handle_alarm(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理闹钟设置"""
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "response": "闹钟已设置",
            "action": "set_alarm"
        }
    
    async def _handle_smart_home(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理智能家居控制"""
        await asyncio.sleep(0.5)
        device = intent_result.get("entities", {}).get("device", "设备")
        return {
            "success": True,
            "response": f"{device}已控制",
            "action": "smart_home_control"
        }
    
    async def _handle_general(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理一般对话"""
        await asyncio.sleep(0.3)
        return {
            "success": True,
            "response": "我明白了，有什么可以帮助您的吗？",
            "action": "general_chat"
        }


class TTSModule:
    """语音合成模块（占位符实现）"""
    
    def __init__(self):
        self.is_speaking = False
    
    async def speak(self, text: str) -> bool:
        """语音合成"""
        logger.info(f"🔊 语音合成: {text}")
        self.is_speaking = True
        
        # 模拟TTS处理时间
        await asyncio.sleep(len(text) * 0.1)  # 根据文本长度模拟时间
        
        logger.info(f"🔊 语音播放完成")
        self.is_speaking = False
        return True
    
    def stop_speaking(self):
        """停止语音播放"""
        self.is_speaking = False
        logger.info("🔊 语音播放已停止")


class VoiceAssistantPipeline:
    """语音助手流水线管理器"""
    
    def __init__(self, model_dir: str = None):
        """
        初始化语音助手流水线
        
        Args:
            model_dir: 模型目录路径
        """
        self.model_dir = model_dir
        
        # 初始化各个模块
        self.vad = SileroVAD(model_dir)
        self.kws = KeywordSpotter(model_dir)
        self.asr = ASRModule()
        self.intent = IntentModule()
        self.executor = CommandExecutor()
        self.tts = TTSModule()
        
        # 流水线状态
        self.state = PipelineState.IDLE
        self.is_running = False
        
        # 事件回调
        self.event_callbacks: List[Callable[[PipelineEvent], None]] = []
        
        # 音频流
        self.kws_stream = None
        
        logger.info("🎯 语音助手流水线初始化完成")
    
    def add_event_callback(self, callback: Callable[[PipelineEvent], None]):
        """添加事件回调"""
        self.event_callbacks.append(callback)
    
    def _emit_event(self, event_type: str, data: Any):
        """发送事件"""
        event = PipelineEvent(
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            state=self.state
        )
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件回调错误: {e}")
    
    async def start_pipeline(self):
        """启动流水线"""
        if self.is_running:
            logger.warning("流水线已在运行中")
            return
        
        self.is_running = True
        self.state = PipelineState.LISTENING
        self.kws_stream = self.kws.create_stream()
        
        logger.info("🎯 语音助手流水线启动")
        self._emit_event("pipeline_started", {"state": self.state.value})
        
        # 开始监听循环
        await self._listening_loop()
    
    async def stop_pipeline(self):
        """停止流水线"""
        self.is_running = False
        self.state = PipelineState.IDLE
        
        # 停止各个模块
        self.asr.stop_recognition()
        self.tts.stop_speaking()
        
        logger.info("🎯 语音助手流水线停止")
        self._emit_event("pipeline_stopped", {"state": self.state.value})
    
    async def process_audio_chunk(self, audio_data: np.ndarray, sample_rate: int = 16000):
        """处理音频数据块"""
        if not self.is_running:
            logger.warning("⚠️ 流水线未运行，忽略音频数据")
            return
        
        try:
            if self.state == PipelineState.LISTENING:
                await self._handle_listening_state(audio_data, sample_rate)
            elif self.state == PipelineState.SPEECH_RECOGNITION:
                # 在语音识别状态下，可以继续收集音频数据
                logger.debug("语音识别状态，继续收集音频数据")
            else:
                logger.debug(f"当前状态: {self.state.value}，忽略音频数据")
            
        except Exception as e:
            logger.error(f"❌ 音频处理错误: {e}")
            import traceback
            logger.error(f"❌ 错误详情: {traceback.format_exc()}")
            try:
                await self._reset_to_listening()
            except Exception as reset_error:
                logger.error(f"❌ 重置流水线失败: {reset_error}")
    
    async def _handle_listening_state(self, audio_data: np.ndarray, sample_rate: int):
        """处理监听状态"""
        # 减少日志频率 - 每20个音频块输出一次
        if hasattr(self, '_audio_count'):
            self._audio_count += 1
        else:
            self._audio_count = 1
            
        if self._audio_count % 20 == 0:
            logger.info(f"🔄 处理音频块: {len(audio_data)} 样本, 范围: [{audio_data.min():.3f}, {audio_data.max():.3f}]")
        
        # 重新启用VAD检测
        has_speech = self.vad.process_audio_chunk(audio_data, sample_rate)
        
        if self._audio_count % 20 == 0:
            logger.info(f"🎤 VAD检测结果: {has_speech}")
        
        if has_speech:
            if self._audio_count % 20 == 0:
                logger.info("🎯 检测到语音活动，进行关键词检测...")
            keyword = self.kws.process_audio_chunk(self.kws_stream, audio_data, sample_rate)
            
            if keyword:
                logger.info(f"🎯 检测到唤醒词: {keyword}")
                self.state = PipelineState.WAKE_WORD_DETECTED
                self._emit_event("wake_word_detected", {"keyword": keyword})
                
                # 进入语音识别阶段
                await self._enter_speech_recognition()
            elif self._audio_count % 20 == 0:
                logger.info("🎯 KWS检测结果: None")
        else:
            if self._audio_count % 20 == 0:
                logger.info("🔇 未检测到语音活动")
            # 即使没有VAD检测到语音，也进行关键词检测（降低VAD依赖）
            keyword = self.kws.process_audio_chunk(self.kws_stream, audio_data, sample_rate)
            if keyword:
                logger.info(f"🎯 检测到唤醒词（无VAD）: {keyword}")
                self.state = PipelineState.WAKE_WORD_DETECTED
                self._emit_event("wake_word_detected", {"keyword": keyword})
                
                # 进入语音识别阶段
                await self._enter_speech_recognition()
    
    async def _enter_speech_recognition(self):
        """进入语音识别阶段"""
        self.state = PipelineState.SPEECH_RECOGNITION
        self._emit_event("speech_recognition_started", {})
        
        # 开始语音识别
        recognized_text = await self.asr.start_recognition()
        
        if recognized_text:
            # 进入意图识别阶段
            await self._enter_intent_processing(recognized_text)
        else:
            # 识别失败，返回监听状态
            await self._reset_to_listening()
    
    async def _enter_intent_processing(self, text: str):
        """进入意图处理阶段"""
        self.state = PipelineState.INTENT_PROCESSING
        self._emit_event("intent_processing_started", {"text": text})
        
        # 识别意图
        intent_result = await self.intent.recognize_intent(text)
        
        # 进入指令执行阶段
        await self._enter_command_execution(intent_result)
    
    async def _enter_command_execution(self, intent_result: Dict[str, Any]):
        """进入指令执行阶段"""
        self.state = PipelineState.EXECUTING_COMMAND
        self._emit_event("command_execution_started", intent_result)
        
        # 执行指令
        execution_result = await self.executor.execute_command(intent_result)
        
        # 进入语音合成阶段
        await self._enter_tts(execution_result)
    
    async def _enter_tts(self, execution_result: Dict[str, Any]):
        """进入语音合成阶段"""
        self.state = PipelineState.SPEAKING
        self._emit_event("tts_started", execution_result)
        
        # 语音合成
        response_text = execution_result.get("response", "处理完成")
        await self.tts.speak(response_text)
        
        # 返回监听状态
        await self._reset_to_listening()
    
    async def _reset_to_listening(self):
        """重置到监听状态"""
        self.state = PipelineState.LISTENING
        self.kws_stream = self.kws.create_stream()  # 重新创建流
        self.vad.reset()  # 重置VAD状态
        
        self._emit_event("returned_to_listening", {})
        logger.info("🔄 返回监听状态")
    
    async def _listening_loop(self):
        """监听循环（用于演示）"""
        while self.is_running:
            await asyncio.sleep(0.1)  # 避免CPU占用过高
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        return {
            "state": self.state.value,
            "is_running": self.is_running,
            "modules": {
                "vad": self.vad.get_model_info(),
                "kws": self.kws.get_model_info(),
                "asr": {"is_processing": self.asr.is_processing},
                "tts": {"is_speaking": self.tts.is_speaking}
            }
        }
