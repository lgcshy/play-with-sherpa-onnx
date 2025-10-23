"""
关键词检测器封装类
"""
import numpy as np
import sherpa_onnx
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

# pypinyin 用于将中文转为拼音（含声母/韵母和声调）
try:
    from pypinyin import pinyin, Style
except Exception:
    pinyin = None
    Style = None

from ..config import MODEL_DIR, CUSTOM_KEYWORDS
from .vad_detector import SileroVAD


class KeywordSpotter:
    """关键词检测器封装类"""
    
    def __init__(self, model_dir: str = None, keywords: List[str] = None):
        """
        初始化关键词检测器
        
        Args:
            model_dir: 模型目录路径
            keywords: 自定义关键词列表
        """
        self.model_dir = Path(model_dir) if model_dir else MODEL_DIR
        self.keywords = keywords or CUSTOM_KEYWORDS
        self.kws = None
        self.keywords_file = None
        
        # 创建关键词文件
        self._create_keywords_file()
        
        # 初始化检测器
        self._initialize_spotter()
        
        # 初始化VAD检测器
        self.vad = SileroVAD(self.model_dir)
    
    def _hanzi_to_token_line(self, text: str) -> str:
        """将中文转换为音素格式"""
        if not pinyin or not Style:
            return text  # 退化：仍然写原文
        
        # 获取每个字的声母、韵母（带调）
        initials = pinyin(text, style=Style.INITIALS, strict=False, errors="ignore")
        finals = pinyin(text, style=Style.FINALS_TONE, strict=False, errors="ignore")

        tokens = []
        for (ini_list, fin_list) in zip(initials, finals):
            ini = (ini_list[0] or "").strip()
            fin = (fin_list[0] or "").strip()
            # 可能遇到非汉字或被忽略内容
            if not ini and not fin:
                continue
            if ini:
                tokens.append(ini)
            if fin:
                tokens.append(fin)
        token_str = " ".join(tokens)
        # 在末尾追加中文展示用标签，便于结果显示
        return f"{token_str} @{text}" if token_str else text

    def _create_keywords_file(self):
        """创建关键词文件"""
        # 创建自定义关键词文件
        self.keywords_file = self.model_dir / "custom_keywords.txt"
        
        # 将中文关键词转换为音素格式
        converted_lines = [self._hanzi_to_token_line(kw) for kw in self.keywords]
        
        with open(self.keywords_file, "w", encoding="utf-8") as f:
            for line in converted_lines:
                f.write(f"{line}\n")
        
        if not pinyin:
            logger.warning("⚠️ 未安装 pypinyin，已按原文写入。建议安装：pip install pypinyin。否则会出现 tokens 无法匹配的错误。")
        
        logger.info(f"✅ 关键词文件已创建: {self.keywords_file}")
        logger.info(f"关键词列表: {self.keywords}")
        logger.debug(f"转换后的音素格式: {converted_lines}")
    
    def _initialize_spotter(self):
        """初始化关键词检测器"""
        try:
            logger.info(f"正在加载模型: {self.model_dir}")
            
            self.kws = sherpa_onnx.KeywordSpotter(
                tokens=str(self.model_dir / "tokens.txt"),
                encoder=str(self.model_dir / "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
                decoder=str(self.model_dir / "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
                joiner=str(self.model_dir / "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"),
                num_threads=2,
                keywords_file=str(self.keywords_file),
                provider="cpu",  # 可改为 "cuda" 如果有 GPU
                max_active_paths=4,
                num_trailing_blanks=1,
                keywords_score=1.0,
                keywords_threshold=0.25,
            )
            
            logger.success("✅ 模型加载成功！")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise
    
    def create_stream(self):
        """创建音频流"""
        if not self.kws:
            raise RuntimeError("检测器未初始化")
        return self.kws.create_stream()
    
    def process_audio_chunk(self, stream, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """
        处理音频数据块（集成VAD和KWS）
        
        Args:
            stream: 音频流对象
            audio_data: 音频数据 (numpy array)
            sample_rate: 采样率
            
        Returns:
            检测到的关键词，如果没有检测到则返回None
        """
        try:
            # 暂时禁用VAD，直接进行关键词检测
            # TODO: 优化VAD参数后再启用
            # has_speech = self.vad.process_audio_chunk(audio_data, sample_rate)
            # if not has_speech:
            #     return None
            
            # 直接进行关键词检测
            stream.accept_waveform(sample_rate, audio_data)
            
            # 检测关键词 - 每次decode_stream后都检查结果
            while self.kws.is_ready(stream):
                self.kws.decode_stream(stream)
                
                # 每次解码后都检查结果
                result = self.kws.get_result(stream)
                keyword = result if isinstance(result, str) else getattr(result, "keyword", "")
                
                if keyword and keyword.strip():
                    logger.info(f"🎯 检测到唤醒词: '{keyword.strip()}'")
                    # 检测到关键词后重置stream状态，以便下次检测
                    self.kws.reset_stream(stream)
                    return keyword.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"音频处理错误: {e}")
            return None
    
    def process_audio_file(self, audio_file: str) -> Optional[str]:
        """
        处理音频文件
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            检测到的关键词
        """
        try:
            import wave
            
            with wave.open(audio_file) as f:
                assert f.getnchannels() == 1, "仅支持单声道音频"
                assert f.getsampwidth() == 2, "仅支持 16-bit 音频"
                
                samples = f.readframes(f.getnframes())
                samples_int16 = np.frombuffer(samples, dtype=np.int16)
                samples_float32 = samples_int16.astype(np.float32) / 32768.0
                
                sample_rate = f.getframerate()
            
            # 创建音频流
            stream = self.create_stream()
            stream.accept_waveform(sample_rate, samples_float32)
            
            # 输入结束信号
            tail_paddings = np.zeros(int(0.3 * sample_rate), dtype=np.float32)
            stream.accept_waveform(sample_rate, tail_paddings)
            stream.input_finished()
            
            # 检测
            while self.kws.is_ready(stream):
                self.kws.decode_stream(stream)
            
            result = self.kws.get_result(stream)
            
            # 兼容不同版本的返回格式
            keyword = result if isinstance(result, str) else getattr(result, "keyword", "")
            
            if keyword and keyword.strip():
                logger.info(f"🎯 文件检测到唤醒词: '{keyword.strip()}'")
                return keyword.strip()
            else:
                logger.info("❌ 文件未检测到唤醒词")
                return None
                
        except Exception as e:
            logger.error(f"文件处理错误: {e}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        kws_info = {
            "model_dir": str(self.model_dir),
            "keywords": self.keywords,
            "keywords_file": str(self.keywords_file),
            "sample_rate": 16000,
            "threshold": 0.25
        }
        
        # 添加VAD信息
        vad_info = self.vad.get_model_info()
        kws_info["vad"] = vad_info
        
        return kws_info
    
    def reset_vad(self):
        """重置VAD状态"""
        if self.vad:
            self.vad.reset()
            logger.debug("关键词检测器VAD状态已重置")
