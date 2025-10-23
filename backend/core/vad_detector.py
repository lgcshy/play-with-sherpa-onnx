"""
基于Sherpa-ONNX的VAD模块
"""
import numpy as np
import sherpa_onnx
from pathlib import Path
from typing import Optional, List, Tuple
from loguru import logger

from ..config import MODEL_DIR


class SileroVAD:
    """基于Sherpa-ONNX的Silero VAD检测器"""
    
    def __init__(self, model_dir: str = None):
        """
        初始化VAD检测器
        
        Args:
            model_dir: 模型目录路径，如果为None则使用默认路径
        """
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.vad = None
        self.sample_rate = 16000
        self.last_speech_state = None  # 记录上次的语音状态
        
        # 初始化VAD检测器
        self._initialize_vad()
    
    def _initialize_vad(self):
        """初始化VAD检测器"""
        try:
            logger.info(f"正在加载Silero VAD模型...")
            
            # 使用Sherpa-ONNX的Silero VAD - 调整参数使其更宽松
            silero_config = sherpa_onnx.SileroVadModelConfig(
                model=f"{self.model_dir}/silero_vad.onnx",
                threshold=0.3,  # 降低阈值，更容易检测到语音
                min_silence_duration=1.0,  # 增加最小静音时间，避免过早截断
                min_speech_duration=0.1,  # 减少最小语音时间，更快响应
                window_size=512,
                max_speech_duration=20.0   # 秒
            )
            
            vad_config = sherpa_onnx.VadModelConfig(
                silero_vad=silero_config,
                sample_rate=16000,
                num_threads=1,
                provider='cpu',
                debug=False
            )
            
            self.vad = sherpa_onnx.VoiceActivityDetector(vad_config)
            
            logger.success("✅ Silero VAD模型加载成功！")
            
        except Exception as e:
            logger.error(f"❌ VAD模型加载失败: {e}")
            # 如果Silero VAD不可用，使用简单的能量检测作为fallback
            logger.warning("使用简单的能量检测作为VAD fallback")
            self.vad = None
    
    def process_audio_chunk(self, audio_data: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        处理音频数据块，检测是否有语音活动
        
        Args:
            audio_data: 音频数据 (numpy array)
            sample_rate: 采样率
            
        Returns:
            是否有语音活动 (True/False)
        """
        try:
            if self.vad:
                # 使用Sherpa-ONNX的Silero VAD检测
                # 将numpy数组转换为Python列表
                samples = audio_data.tolist()
                
                # 输入音频数据到VAD检测器
                self.vad.accept_waveform(samples)
                
                # 检查是否检测到语音
                is_speech = self.vad.is_speech_detected()
                
                # 只在语音状态变化时打印日志
                if self.last_speech_state != is_speech:
                    if is_speech:
                        logger.info("🎤 VAD检测：语音开始")
                    else:
                        logger.info("🔇 VAD检测：语音结束")
                        # 语音结束时，重置VAD状态以便下次检测
                        self.vad.flush()
                    self.last_speech_state = is_speech
                
                return is_speech
            else:
                # Fallback: 使用简单的能量检测
                return self._simple_energy_vad(audio_data)
                
        except Exception as e:
            logger.error(f"VAD处理错误: {e}")
            # 出错时默认认为有语音活动，避免丢失语音
            return True
    
    def reset(self):
        """重置VAD状态"""
        if self.vad:
            self.vad.reset()
            self.last_speech_state = None
            logger.debug("VAD状态已重置")
    
    def _simple_energy_vad(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """
        简单的能量检测VAD (fallback)
        
        Args:
            audio_data: 音频数据
            threshold: 能量阈值
            
        Returns:
            是否有语音活动
        """
        # 计算RMS能量
        rms_energy = np.sqrt(np.mean(audio_data ** 2))
        
        # 简单的能量阈值检测
        is_speech = rms_energy > threshold
        
        return is_speech
    
    def get_model_info(self) -> dict:
        """获取VAD模型信息"""
        return {
            "model_type": "Silero VAD" if self.vad else "Simple Energy VAD",
            "model_dir": str(self.model_dir),
            "sample_rate": self.sample_rate,
            "threshold": 0.5 if self.vad else 0.01,
            "min_silence_duration_ms": 500 if self.vad else None,
            "min_speech_duration_ms": 250 if self.vad else None,
        }