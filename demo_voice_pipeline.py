#!/usr/bin/env python3
"""
语音助手流水线演示
展示完整的语音处理流程：VAD -> KWS -> ASR -> 意图识别 -> 执行指令 -> TTS
"""
import asyncio
import sys
import numpy as np
from pathlib import Path
from loguru import logger

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.core.voice_assistant_pipeline import VoiceAssistantPipeline, PipelineEvent


class PipelineDemo:
    """流水线演示类"""
    
    def __init__(self):
        self.pipeline = VoiceAssistantPipeline()
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """设置事件处理器"""
        self.pipeline.add_event_callback(self.on_pipeline_event)
    
    def on_pipeline_event(self, event: PipelineEvent):
        """处理流水线事件"""
        logger.info(f"📢 流水线事件: {event.event_type} - 状态: {event.state.value}")
        
        if event.event_type == "wake_word_detected":
            logger.success(f"🎯 唤醒词: {event.data['keyword']}")
        elif event.event_type == "speech_recognition_started":
            logger.info("🎤 开始语音识别...")
        elif event.event_type == "intent_processing_started":
            logger.info(f"🧠 意图识别: {event.data['text']}")
        elif event.event_type == "command_execution_started":
            logger.info(f"⚡ 执行指令: {event.data['intent']}")
        elif event.event_type == "tts_started":
            logger.info(f"🔊 语音合成: {event.data['response']}")
        elif event.event_type == "returned_to_listening":
            logger.info("🔄 返回监听状态")
    
    async def simulate_audio_input(self):
        """模拟音频输入"""
        logger.info("🎵 开始模拟音频输入...")
        
        # 模拟静音
        await asyncio.sleep(2.0)
        silence = np.zeros(1600, dtype=np.float32)  # 100ms静音
        await self.pipeline.process_audio_chunk(silence)
        
        # 模拟唤醒词音频
        logger.info("🎤 模拟唤醒词音频...")
        wake_word_audio = np.random.normal(0, 0.1, 8000).astype(np.float32)  # 500ms音频
        await self.pipeline.process_audio_chunk(wake_word_audio)
        
        # 模拟语音音频
        await asyncio.sleep(1.0)
        logger.info("🎤 模拟语音音频...")
        speech_audio = np.random.normal(0, 0.15, 16000).astype(np.float32)  # 1s音频
        await self.pipeline.process_audio_chunk(speech_audio)
        
        # 等待处理完成
        await asyncio.sleep(5.0)
    
    async def run_demo(self):
        """运行演示"""
        logger.info("🚀 启动语音助手流水线演示")
        
        try:
            # 启动流水线
            pipeline_task = asyncio.create_task(self.pipeline.start_pipeline())
            
            # 等待流水线启动
            await asyncio.sleep(1.0)
            
            # 模拟音频输入
            await self.simulate_audio_input()
            
            # 停止流水线
            await self.pipeline.stop_pipeline()
            
            # 等待流水线任务完成
            await pipeline_task
            
            logger.success("✅ 演示完成")
            
        except Exception as e:
            logger.error(f"❌ 演示出错: {e}")
            await self.pipeline.stop_pipeline()
    
    def print_pipeline_status(self):
        """打印流水线状态"""
        status = self.pipeline.get_pipeline_status()
        logger.info("📊 流水线状态:")
        logger.info(f"  状态: {status['state']}")
        logger.info(f"  运行中: {status['is_running']}")
        logger.info(f"  模块状态:")
        for module, info in status['modules'].items():
            logger.info(f"    {module}: {info}")


async def main():
    """主函数"""
    demo = PipelineDemo()
    
    # 打印初始状态
    demo.print_pipeline_status()
    
    # 运行演示
    await demo.run_demo()
    
    # 打印最终状态
    demo.print_pipeline_status()


if __name__ == "__main__":
    # 设置日志级别
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    # 运行演示
    asyncio.run(main())
