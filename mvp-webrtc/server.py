import asyncio
import json
import os
from datetime import datetime
from typing import Optional

import av
from fractions import Fraction
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import time

# 先尝试预加载 onnxruntime，再导入 sherpa_onnx，避免找不到 libonnxruntime.so
try:
    import onnxruntime  # noqa: F401
except Exception:
    pass
try:
    import sherpa_onnx
except Exception as e:
    sherpa_onnx = None
    print("[WARN] sherpa_onnx not available:", e)

ROOT = os.path.dirname(__file__)
STATIC_DIR = os.path.join(ROOT, "static")
SAMPLE_WAV = os.path.join(ROOT, 'sample.wav')

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def init_kws():
    if sherpa_onnx is None:
        return None
    # 模型目录：优先使用仓库现有的 zipformer 模型
    model_dir = os.path.normpath(os.path.join(ROOT, "..", "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"))
    tokens = os.path.join(model_dir, "tokens.txt")
    enc = os.path.join(model_dir, "encoder-epoch-12-avg-2-chunk-16-left-64.onnx")
    dec = os.path.join(model_dir, "decoder-epoch-12-avg-2-chunk-16-left-64.onnx")
    joi = os.path.join(model_dir, "joiner-epoch-12-avg-2-chunk-16-left-64.onnx")

    # 关键词文件：优先使用仓库根的 my_keywords.txt，否则回退模型自带 keywords.txt
    repo_keywords = os.path.normpath(os.path.join(ROOT, "..", "my_keywords.txt"))
    model_keywords = os.path.join(model_dir, "keywords.txt")
    keywords_file = repo_keywords if os.path.exists(repo_keywords) else model_keywords

    if not (os.path.exists(tokens) and os.path.exists(enc) and os.path.exists(dec) and os.path.exists(joi) and os.path.exists(keywords_file)):
        print("[WARN] KWS model or keywords not found; KWS disabled.")
        return None

    print(f"[KWS] Loading model from {model_dir}\n       keywords: {keywords_file}")
    kws = sherpa_onnx.KeywordSpotter(
        tokens=tokens,
        encoder=enc,
        decoder=dec,
        joiner=joi,
        num_threads=2,
        keywords_file=keywords_file,
        provider="cpu",
        max_active_paths=4,
        num_trailing_blanks=1,
        keywords_score=1.0,
        keywords_threshold=0.25,
    )
    print("[KWS] Ready")
    return kws


app.state.kws = init_kws()


class ServerAudioSink(MediaStreamTrack):
    kind = "audio"

    def __init__(self, track: MediaStreamTrack):
        super().__init__()
        self.track = track
        self._stopped = False

    async def recv(self):
        # 直接消费上行帧；这里不转发。
        frame = await self.track.recv()
        # 在此处可以提取 PCM 并重采样到 16k，供 KWS 使用
        # 示例：samples = frame.to_ndarray(format='s16')  # shape=(channels, samples)
        # 使用 av.AudioResampler 将 samples 转为 16k/mono 后送入 KWS
        return frame


class SilenceAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, sample_rate: int = 48000, channels: int = 1):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self._ts = 0

    async def recv(self):
        await asyncio.sleep(0.02)  # 20ms 帧间隔
        samples = int(self.sample_rate * 0.02)  # 20ms
        frame = av.AudioFrame(format="s16", layout="mono", samples=samples)
        # 填充静音
        for p in frame.planes:
            p.update(b"\x00" * p.buffer_size)
        frame.pts = self._ts
        frame.sample_rate = self.sample_rate
        frame.time_base = Fraction(1, self.sample_rate)
        self._ts += samples
        return frame


class Session:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.pc = RTCPeerConnection()
        self.player: Optional[MediaPlayer] = None
        self.control_dc = None
        self._audio_task: Optional[asyncio.Task] = None
        self.kws_stream = app.state.kws.create_stream() if getattr(app.state, "kws", None) else None
        self._last_trigger_time = 0.0
        self._down_attached = False

        # 注册事件回调
        self.pc.on("datachannel")(self._on_datachannel)
        self.pc.on("track")(self._on_track)
        self.pc.on("iceconnectionstatechange")(self._on_ice_state)

    async def send_event(self, data: dict):
        # DataChannel 优先，否则走 WS
        payload = json.dumps(data)
        if self.control_dc and self.control_dc.readyState == "open":
            self.control_dc.send(payload)
        else:
            await self.ws.send_json({"type": "event", "data": data})

    async def close(self):
        await self.pc.close()

    def ensure_downstream_track(self):
        if self._down_attached:
            return
        added = False
        if os.path.exists(SAMPLE_WAV):
            try:
                self.player = MediaPlayer(SAMPLE_WAV)
                if self.player.audio:
                    self.pc.addTrack(self.player.audio)
                    added = True
            except Exception as e:
                print("[PC] MediaPlayer error, fallback to silence:", e)
        if not added:
            self.pc.addTrack(SilenceAudioTrack())
        self._down_attached = True

    # --- event handlers ---
    def _on_datachannel(self, channel):
        self.control_dc = channel
        @channel.on("message")
        def on_message(message):
            print("[DC] message:", message)

    def _on_track(self, track):
        print("[PC] Track received:", track.kind)
        if track.kind == "audio":
            async def consume_audio():
                resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
                while True:
                    try:
                        frame = await track.recv()
                        try:
                            f16 = resampler.resample(frame)
                            pcm = b"".join(p.to_bytes() for p in f16.planes)
                            import numpy as _np
                            samples = _np.frombuffer(pcm, dtype=_np.int16).astype(_np.float32) / 32768.0
                            if self.kws_stream is not None and app.state.kws is not None:
                                self.kws_stream.accept_waveform(16000, samples)
                                while app.state.kws.is_ready(self.kws_stream):
                                    app.state.kws.decode_stream(self.kws_stream)
                                    result = app.state.kws.get_result(self.kws_stream)
                                    kw = result if isinstance(result, str) else getattr(result, "keyword", "")
                                    if kw:
                                        now = time.monotonic()
                                        if now - self._last_trigger_time > 1.5:
                                            self._last_trigger_time = now
                                            await self.send_event({"type": "kws", "keyword": kw, "ts": datetime.utcnow().isoformat()})
                        except Exception:
                            pass
                    except Exception:
                        break
            self._audio_task = asyncio.create_task(consume_audio())
        # 确保已添加下行轨
        self.ensure_downstream_track()

    def _on_ice_state(self):
        print("ICE state:", self.pc.iceConnectionState)


@app.websocket("/ws")
async def ws_signaling(ws: WebSocket):
    await ws.accept()
    session = Session(ws)
    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            if data["type"] == "offer":
                offer = RTCSessionDescription(sdp=data["desc"]["sdp"], type=data["desc"]["type"])
                await session.pc.setRemoteDescription(offer)
                # 确保在创建 answer 前加入下行轨，便于协商
                session.ensure_downstream_track()
                # 创建 answer
                await session.pc.setLocalDescription(await session.pc.createAnswer())
                await ws.send_json({"type": "answer", "desc": {
                    "sdp": session.pc.localDescription.sdp,
                    "type": session.pc.localDescription.type
                }})
                # 下发一个欢迎事件
                await session.send_event({"type": "hello", "ts": datetime.utcnow().isoformat()})
            # 非 trickle ICE：不接收逐条 ICE 候选
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()


if __name__ == "__main__":
    print("Running server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
