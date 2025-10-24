"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 模型配置
MODEL_DIR = PROJECT_ROOT / "models" / "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"

# 自定义唤醒词配置 - 四个字唤醒词，使用最极端的参数
# 格式: "唤醒词 :boosting_score #trigger_threshold"
CUSTOM_KEYWORDS = [
    "你好小立 :50.0 #0.001",    # 四个字唤醒词，极高提升分数，极低阈值
    "小立小立 :40.0 #0.001",    # 四个字唤醒词，很高提升分数，极低阈值
    "小立同学 :40.0 #0.001"     # 四个字唤醒词，很高提升分数，极低阈值
]

# 音频配置
SAMPLE_RATE = 16000
CHUNK_SIZE = int(0.1 * SAMPLE_RATE)  # 100ms chunks

# WebSocket配置
WS_MAX_CONNECTIONS = 100
WS_HEARTBEAT_INTERVAL = 30

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
