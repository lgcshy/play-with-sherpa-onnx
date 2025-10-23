# Sherpa-ONNX 中文唤醒词实时检测系统

基于 FastAPI + WebSocket + Sherpa-ONNX 的中文唤醒词实时检测系统，支持前端录音通过 WebSocket 发送音频数据到后端进行实时检测。

## 🚀 功能特性

- ✅ **实时音频处理**: 支持流式音频数据接收和处理
- ✅ **WebSocket通信**: 低延迟的双向通信
- ✅ **多关键词检测**: 支持多个唤醒词同时检测
- ✅ **自定义关键词**: 可配置自定义唤醒词
- ✅ **Web界面**: 内置简单的录音和检测界面
- ✅ **RESTful API**: 提供状态查询和模型信息接口

## 📋 系统要求

- Python 3.12.9+
- uv (Python包管理器)
- 支持WebSocket的现代浏览器

## 🛠️ 安装和运行

### 1. 环境准备

```bash
# 安装uv (如果未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 进入项目目录
cd /path/to/sherpa_onnx_demo
```

### 2. 安装依赖

```bash
# 使用uv安装依赖
uv sync
```

### 3. 启动服务器

```bash
# 启动开发服务器
uv run python run.py

# 或者直接运行
./run.py
```

服务器将在 `http://192.168.73.130:8000` 启动。

### 4. 访问Web界面

打开浏览器访问 `http://192.168.73.130:8000`，即可使用内置的录音和检测界面。

## 🎯 支持的唤醒词

当前系统支持以下唤醒词（基于预训练模型）：

- 小爱同学
- 你好问问  
- 小艺小艺
- 你好军哥
- 蛋哥蛋哥
- 小米小米
- 林美丽
- 你好西西

## 📡 API接口

### REST API

- `GET /` - Web界面
- `GET /api/status` - 服务器状态
- `GET /api/model-info` - 模型信息

### WebSocket API

- `WS /ws` - 音频数据流接口

#### WebSocket消息格式

**发送**: 音频数据 (PCM 16-bit, 16kHz, 单声道)
**接收**: JSON格式的检测结果

```json
{
  "type": "keyword_detected",
  "keyword": "小爱同学",
  "timestamp": 1234567890.123
}
```

## 🧪 测试

### 使用测试客户端

```bash
# 基本连接测试
uv run python test_client.py

# 使用音频文件测试
uv run python test_client.py file
```

### 手动测试

1. 访问 `http://192.168.73.130:8000`
2. 点击"连接"按钮
3. 点击"开始录音"按钮
4. 说出支持的唤醒词
5. 观察检测结果

## 📁 项目结构

```
sherpa_onnx_demo/
├── backend/                 # 后端代码
│   ├── api/                # API路由
│   ├── core/               # 核心功能
│   │   └── keyword_spotter.py  # 关键词检测器
│   ├── models/             # 数据模型
│   ├── utils/              # 工具函数
│   ├── config.py           # 配置文件
│   └── main.py             # FastAPI应用
├── models/                 # 模型文件
│   └── sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/
├── frontend/               # 前端代码 (待开发)
├── static/                 # 静态文件
├── templates/              # 模板文件
├── tests/                  # 测试文件
├── pyproject.toml         # 项目配置
├── run.py                  # 启动脚本
├── test_client.py          # 测试客户端
└── README.md               # 项目说明
```

## ⚙️ 配置

主要配置在 `backend/config.py` 中：

```python
# 音频配置
SAMPLE_RATE = 16000
CHUNK_SIZE = int(0.1 * SAMPLE_RATE)  # 100ms chunks

# WebSocket配置
WS_MAX_CONNECTIONS = 100
WS_HEARTBEAT_INTERVAL = 30

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000
```

## 🔧 开发

### 添加新的唤醒词

1. 修改 `backend/config.py` 中的 `CUSTOM_KEYWORDS`
2. 确保关键词在模型的 `tokens.txt` 中有对应的音素表示
3. 重启服务器

### 调试模式

```bash
# 设置环境变量启用调试模式
export DEBUG=true
uv run python run.py
```

## 📊 性能指标

- **检测延迟**: < 200ms
- **并发连接**: 支持100+用户
- **音频格式**: PCM 16-bit, 16kHz, 单声道
- **处理块大小**: 100ms (1600 samples)

## 🐛 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型文件路径是否正确
   - 确保有足够的系统内存

2. **WebSocket连接失败**
   - 检查服务器是否正常运行
   - 确认端口8000未被占用

3. **音频检测不准确**
   - 确保音频质量良好
   - 检查麦克风权限设置
   - 调整检测阈值参数

## 📄 许可证

本项目基于MIT许可证开源。

## 🙏 致谢

- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) - 语音识别引擎
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [Wenetspeech](https://wenet.org.cn/Wenetspeech/) - 中文语音数据集
