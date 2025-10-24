# Xiaoli KWS FastAPI WebSocket 系统

基于FastAPI和WebSocket的实时关键词检测系统，支持PCM音频流传输。

## 功能特性

- 🎯 **实时关键词检测**: 基于Sherpa-ONNX的高性能关键词检测
- 🔌 **WebSocket支持**: 实时双向通信，支持PCM音频流传输
- 🎨 **现代化UI**: 基于Bootstrap和Jinja2模板的响应式界面
- 📊 **实时可视化**: 音频波形实时显示
- ⚙️ **动态配置**: 支持运行时调整检测参数和唤醒词
- 📝 **日志系统**: 完整的检测日志和统计信息
- 🎵 **VAD支持**: 语音活动检测，减少误触发

## 系统架构

```
前端 (JavaScript) 
    ↓ WebSocket (PCM音频流)
FastAPI WebSocket服务器
    ↓ 音频处理
KWS引擎 (Sherpa-ONNX)
    ↓ 检测结果
VAD检测器
    ↓ 结果返回
前端显示
```

## 安装和运行

### 1. 安装依赖

```bash
# 使用uv安装依赖
uv sync

# 或使用pip
pip install -e .
```

### 2. 准备模型文件

确保以下模型文件存在于 `xiaoli/model_data/kws/` 目录：

- `tokens.txt`
- `encoder-epoch-12-avg-2-chunk-16-left-64.onnx`
- `decoder-epoch-12-avg-2-chunk-16-left-64.onnx`
- `joiner-epoch-12-avg-2-chunk-16-left-64.onnx`
- `text/keyword_token.txt`

### 3. 启动服务器

```bash
# 使用启动脚本
python xiaoli/run.py

# 或直接使用uvicorn
uvicorn xiaoli.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问Web界面

打开浏览器访问: http://localhost:8000

## WebSocket API

### 连接端点

- **KWS处理**: `ws://localhost:8000/ws/kws`
- **日志流**: `ws://localhost:8000/ws/logs`

### 消息格式

#### 发送音频数据

```json
{
    "type": "audio_data",
    "audio_data": "base64_encoded_pcm_data",
    "sample_rate": 16000,
    "channels": 1,
    "timestamp": 1234567890.123
}
```

#### 控制命令

```json
// 开始检测
{
    "type": "start_detection"
}

// 停止检测
{
    "type": "stop_detection"
}
```

#### 接收检测结果

```json
{
    "type": "detection",
    "keyword": "小莉",
    "confidence": 0.85,
    "timestamp": "2024-01-01T12:00:00.000Z",
    "processing_time": 15.5
}
```

## HTTP API

### 设置管理

```bash
# 获取当前设置
GET /api/settings

# 更新设置
POST /api/settings
{
    "threshold": 0.25,
    "score": 1.0,
    "max_active_paths": 4,
    "num_trailing_blanks": 1,
    "num_threads": 2,
    "provider": "cpu"
}
```

### 关键词管理

```bash
# 更新关键词
POST /api/keywords
{
    "keywords": ["小莉", "你好小莉", "助手"]
}
```

### 日志管理

```bash
# 获取日志
GET /api/logs

# 清空日志
DELETE /api/logs
```

### 系统状态

```bash
# 获取系统状态
GET /api/status

# 获取统计信息
GET /api/stats
```

## 测试客户端

使用提供的测试客户端验证WebSocket功能：

```bash
python xiaoli/test_client.py
```

测试客户端支持：
- 正弦波测试
- 音频文件测试
- 实时检测结果显示

## 配置说明

### 环境变量

- `HOST`: 服务器主机地址 (默认: 0.0.0.0)
- `PORT`: 服务器端口 (默认: 8000)
- `DEBUG`: 调试模式 (默认: false)
- `RELOAD`: 自动重载 (默认: true)

### KWS参数

- `threshold`: 检测阈值 (0.1-1.0)
- `score`: 关键词分数 (0.1-2.0)
- `max_active_paths`: 最大活跃路径 (1-10)
- `num_trailing_blanks`: 尾随空白数 (0-5)
- `num_threads`: 线程数 (1-8)
- `provider`: 计算提供者 (cpu/cuda)

## 开发说明

### 项目结构

```
xiaoli/
├── app.py              # FastAPI主应用
├── kws.py              # KWS引擎
├── vad.py              # VAD检测器
├── run.py              # 启动脚本
├── test_client.py      # 测试客户端
├── templates/          # Jinja2模板
│   ├── kws.html        # 基础模板
│   ├── index.html      # 主页
│   ├── settings.html   # 设置页
│   └── logs.html       # 日志页
└── static/             # 静态文件
    ├── css/kws.css     # 样式文件
    └── js/kws.js       # JavaScript
```

### 扩展功能

1. **添加新的检测算法**: 在 `kws.py` 中扩展 `KWSEngine` 类
2. **自定义VAD算法**: 在 `vad.py` 中修改 `VADDetector` 类
3. **新的WebSocket端点**: 在 `app.py` 中添加新的WebSocket处理器
4. **UI组件**: 在 `templates/` 和 `static/` 中添加新页面和样式

## 故障排除

### 常见问题

1. **模型文件未找到**
   - 检查 `xiaoli/model_data/kws/` 目录是否存在
   - 确认所有必需的.onnx文件都已下载

2. **WebSocket连接失败**
   - 检查服务器是否正在运行
   - 确认防火墙设置允许WebSocket连接

3. **音频检测不工作**
   - 检查浏览器麦克风权限
   - 确认音频格式为16kHz单声道PCM

4. **性能问题**
   - 调整 `num_threads` 参数
   - 考虑使用GPU加速 (`provider: "cuda"`)

### 日志调试

启用详细日志：

```bash
DEBUG=true python xiaoli/run.py
```

## 许可证

本项目基于MIT许可证开源。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！
