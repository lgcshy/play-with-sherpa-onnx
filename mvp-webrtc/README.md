# WebRTC MVP（FastAPI + aiortc）

最小可行性验证：
- 浏览器上行麦克风（Opus） -> 服务器（aiortc）
- 服务器通过 DataChannel 下发 JSON 事件
- 服务器向浏览器下行音频（Opus），此处用本地 WAV 代替 TTS（可后续接入 TTS）

## 目录
- `server.py`：FastAPI + aiortc 服务端，含简易信令（WS）
- `static/index.html`：前端页面，建立 WebRTC，发送/接收音频与 DataChannel
- `sample.wav`：演示下行播放的 WAV（可替换）
- `requirements.txt`：依赖

## 快速开始
1) 使用 uv 安装依赖（推荐，需 Python 3.10+）
```bash
cd mvp-webrtc
uv sync
uv run uvicorn server:app --host 127.0.0.1 --port 8000
```

或使用定义的脚本：
```bash
uv run -s serve  # 或 uv run -s serve-reload
```

若未安装 uv，可用 pip 备选：
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) 运行服务端
```bash
python server.py
```
默认监听 http://127.0.0.1:8000

3) 打开浏览器访问 http://127.0.0.1:8000
- 允许麦克风权限
- 你会看到连接建立、DataChannel 消息、以及下行音频播放（服务器循环推送 `sample.wav`）。

## 说明
- 这是最小骨架：
  - WebSocket 仅做信令（/ws）
  - WebRTC 承载上行/下行音频与 DataChannel
- 后续对接 sherpa-onnx：
  - 在 `ServerAudioSink.on_frame` 里可拿到上行 PCM，重采样到 16k 后喂给 KWS；
  - 在检测到唤醒后，调用 `DownstreamAudioTrack.enqueue_pcm()` 或替换为 TTS 的 PCM 源；
  - 通过 `control` DataChannel 向前端发送事件（例如唤醒词命中）。

## 常见问题
- 若浏览器无声：检查是否有用户交互后才能自动播放；可点击页面上的“开始”按钮触发播放策略。
- 内网/本机可不配 STUN/TURN；公网或 NAT 复杂网络请自行配置。
