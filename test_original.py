#!/usr/bin/env python3
"""
使用原始示例代码测试关键词检测
"""
import sys
import wave
import numpy as np
import sherpa_onnx
from pathlib import Path

def read_wave(wave_filename: str):
    """读取 WAV 文件"""
    with wave.open(wave_filename) as f:
        assert f.getnchannels() == 1, "仅支持单声道音频"
        assert f.getsampwidth() == 2, "仅支持 16-bit 音频"
        
        samples = f.readframes(f.getnframes())
        samples_int16 = np.frombuffer(samples, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768.0
        
        return samples_float32, f.getframerate()

def create_keyword_spotter(model_dir: str, keywords_file: str):
    """创建唤醒词检测器"""
    print(f"正在加载模型: {model_dir}")
    
    kws = sherpa_onnx.KeywordSpotter(
        tokens=f"{model_dir}/tokens.txt",
        encoder=f"{model_dir}/encoder-epoch-12-avg-2-chunk-16-left-64.onnx",
        decoder=f"{model_dir}/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
        joiner=f"{model_dir}/joiner-epoch-12-avg-2-chunk-16-left-64.onnx",
        num_threads=2,
        keywords_file=keywords_file,
        provider="cpu",
        max_active_paths=4,
        num_trailing_blanks=1,
        keywords_score=1.0,
        keywords_threshold=0.25,
    )
    
    print("✅ 模型加载成功！")
    return kws

def detect_from_file(kws, audio_file: str):
    """从音频文件检测唤醒词"""
    print(f"\n📁 处理文件: {audio_file}")
    
    samples, sample_rate = read_wave(audio_file)
    
    # 创建音频流
    stream = kws.create_stream()
    stream.accept_waveform(sample_rate, samples)
    
    # 输入结束信号
    tail_paddings = np.zeros(int(0.3 * sample_rate), dtype=np.float32)
    stream.accept_waveform(sample_rate, tail_paddings)
    stream.input_finished()
    
    # 检测
    while kws.is_ready(stream):
        kws.decode_stream(stream)
    
    result = kws.get_result(stream)
    
    if result and hasattr(result, 'keyword') and result.keyword:
        print(f"🎯 检测到唤醒词: {result.keyword}")
        keyword = result.keyword
    else:
        print("❌ 未检测到唤醒词")
        keyword = None
    
    return keyword

def main():
    # 配置
    MODEL_DIR = "./models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"
    KEYWORDS_FILE = f"{MODEL_DIR}/keywords.txt"
    
    # 创建检测器
    kws = create_keyword_spotter(MODEL_DIR, KEYWORDS_FILE)
    
    # 测试文件检测
    test_files = [
        f"{MODEL_DIR}/test_wavs/0.wav",
        f"{MODEL_DIR}/test_wavs/1.wav",
        f"{MODEL_DIR}/test_wavs/2.wav",
        f"{MODEL_DIR}/test_wavs/3.wav",
    ]
    
    for audio_file in test_files:
        try:
            detect_from_file(kws, audio_file)
        except FileNotFoundError:
            print(f"⚠️  文件不存在: {audio_file}")

if __name__ == "__main__":
    main()
