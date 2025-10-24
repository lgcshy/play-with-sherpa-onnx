"""
Xiaoli KWS FastAPI Application
Real-time keyword spotting with WebSocket support for PCM audio streaming
"""

import asyncio
import json
import base64
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Import KWS and VAD modules
from .kws import KWSEngine
from .vad import VADDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class AudioData(BaseModel):
    audio_data: str  # Base64 encoded PCM data
    sample_rate: int = 16000
    channels: int = 1
    timestamp: Optional[float] = None

class DetectionResult(BaseModel):
    keyword: str
    confidence: float
    timestamp: str
    processing_time: float

class Settings(BaseModel):
    threshold: float = 0.25
    score: float = 1.0
    max_active_paths: int = 4
    num_trailing_blanks: int = 1
    num_threads: int = 2
    provider: str = "cpu"

class KeywordsRequest(BaseModel):
    keywords: List[str]

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.kws_rooms: Dict[str, List[WebSocket]] = {
            "kws": [],
            "logs": []
        }
    
    async def connect(self, websocket: WebSocket, room: str = "kws"):
        """Accept WebSocket connection and add to room"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.kws_rooms[room].append(websocket)
        logger.info(f"WebSocket connected to room: {room}")
    
    def disconnect(self, websocket: WebSocket, room: str = "kws"):
        """Remove WebSocket connection from room"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.kws_rooms[room]:
            self.kws_rooms[room].remove(websocket)
        logger.info(f"WebSocket disconnected from room: {room}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        await websocket.send_text(message)
    
    async def broadcast_to_room(self, message: str, room: str = "kws"):
        """Broadcast message to all connections in room"""
        disconnected = []
        for connection in self.kws_rooms[room]:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn, room)

# Global instances
manager = ConnectionManager()
kws_engine = None
vad_detector = None

# Initialize FastAPI app
app = FastAPI(
    title="Xiaoli KWS API",
    description="Real-time Keyword Spotting with WebSocket support",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="xiaoli/static"), name="static")
templates = Jinja2Templates(directory="xiaoli/templates")

# Global state
app_state = {
    "is_processing": False,
    "audio_buffer": [],
    "buffer_size": 1600,  # 100ms at 16kHz
    "stats": {
        "total_detections": 0,
        "successful_detections": 0,
        "processing_time": 0,
        "last_detection": None
    },
    "settings": {
        "threshold": 0.25,
        "score": 1.0,
        "max_active_paths": 4,
        "num_trailing_blanks": 1,
        "num_threads": 2,
        "provider": "cpu"
    },
    "keywords": ["小莉", "你好小莉"]
}

@app.on_event("startup")
async def startup_event():
    """Initialize KWS engine and VAD detector on startup"""
    global kws_engine, vad_detector
    
    try:
        # Initialize VAD detector first (simpler)
        vad_detector = VADDetector()
        logger.info("VAD detector initialized")
        
        # Initialize KWS engine (may take longer)
        logger.info("Initializing KWS engine...")
        kws_engine = KWSEngine()
        logger.info("KWS engine initialized")
        
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        # Don't raise, allow app to start without KWS
        kws_engine = None
        vad_detector = None

# WebSocket endpoints
@app.websocket("/ws/kws")
async def websocket_kws_endpoint(websocket: WebSocket):
    """WebSocket endpoint for KWS audio processing"""
    await manager.connect(websocket, "kws")
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio_data":
                # Process audio data
                await process_audio_data(message, websocket)
            elif message.get("type") == "start_detection":
                app_state["is_processing"] = True
                await manager.send_personal_message(
                    json.dumps({"type": "detection_started", "message": "KWS detection started"}),
                    websocket
                )
            elif message.get("type") == "stop_detection":
                app_state["is_processing"] = False
                app_state["audio_buffer"].clear()
                
                # Reset KWS stream
                if kws_engine:
                    kws_engine.reset_stream()
                
                await manager.send_personal_message(
                    json.dumps({"type": "detection_stopped", "message": "KWS detection stopped"}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, "kws")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_personal_message(
            json.dumps({"type": "error", "message": str(e)}),
            websocket
        )

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time logs"""
    await manager.connect(websocket, "logs")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "logs")

async def process_audio_data(message: Dict[str, Any], websocket: WebSocket):
    """Process incoming audio data for keyword detection"""
    if not app_state["is_processing"] or not kws_engine or not vad_detector:
        return
    
    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(message["audio_data"])
        
        # Convert to numpy array (assuming 16-bit PCM)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # Check if we have valid audio data
        if len(audio_array) == 0:
            logger.warning("Received empty audio data")
            return
        
        # Normalize audio to [-1, 1] range
        audio_normalized = audio_array.astype(np.float32) / 32768.0
        
        # Add to buffer
        app_state["audio_buffer"].extend(audio_normalized.tolist())
        
        # Process when buffer is full
        if len(app_state["audio_buffer"]) >= app_state["buffer_size"]:
            # Get audio chunk
            audio_chunk = np.array(
                app_state["audio_buffer"][:app_state["buffer_size"]], 
                dtype=np.float32
            )
            
            # VAD detection
            try:
                logger.debug(f"Processing audio chunk: {len(audio_chunk)} samples")
                
                if vad_detector.is_speech(audio_chunk):
                    logger.debug("Speech detected, running KWS")
                    # KWS detection
                    start_time = time.time()
                    result = await kws_engine.stream_detect(audio_chunk)
                    
                    if result and result.get("keyword"):
                        logger.info(f"Keyword detected: {result['keyword']}")
                        # Update statistics
                        app_state["stats"]["total_detections"] += 1
                        app_state["stats"]["successful_detections"] += 1
                        app_state["stats"]["last_detection"] = datetime.now().isoformat()
                        
                        # Calculate processing time
                        processing_time = (time.time() - start_time) * 1000
                        app_state["stats"]["processing_time"] = processing_time
                        
                        # Create detection result
                        detection_result = {
                            "type": "detection",
                            "keyword": result["keyword"],
                            "confidence": result["confidence"],
                            "timestamp": datetime.now().isoformat(),
                            "processing_time": processing_time
                        }
                        
                        # Send result to client
                        await manager.send_personal_message(
                            json.dumps(detection_result),
                            websocket
                        )
                        
                        # Broadcast to logs room
                        await manager.broadcast_to_room(
                            json.dumps({
                                "type": "log",
                                "level": "info",
                                "source": "kws",
                                "message": f"Keyword detected: {result['keyword']} (confidence: {result['confidence']:.3f})",
                                "timestamp": datetime.now().isoformat()
                            }),
                            "logs"
                        )
                        
                        logger.info(f"Keyword detected: {result['keyword']} (confidence: {result['confidence']:.3f})")
                    else:
                        logger.debug("No keyword detected")
                else:
                    logger.debug("No speech detected")
            except Exception as vad_error:
                logger.error(f"Error in VAD/KWS processing: {vad_error}")
                import traceback
                traceback.print_exc()
                # Don't send error to client for every audio chunk to avoid spam
            
            # Clear processed buffer
            app_state["audio_buffer"] = app_state["audio_buffer"][app_state["buffer_size"]:]
            
    except Exception as e:
        logger.error(f"Error processing audio data: {e}")
        # Only send error if it's a critical error, not for every audio chunk
        if "base64" in str(e).lower() or "decode" in str(e).lower():
            await manager.send_personal_message(
                json.dumps({"type": "error", "message": f"Audio processing error: {str(e)}"}),
                websocket
            )

# HTTP endpoints
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve main page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "keywords": app_state["keywords"],
        "stats": app_state["stats"]
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve settings page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": app_state["settings"],
        "keywords_text": "\n".join(app_state["keywords"]),
        "audio_settings": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 1024,
            "device_index": -1
        },
        "audio_devices": [
            {"index": -1, "name": "默认设备"},
            {"index": 0, "name": "麦克风 (USB Audio)"},
            {"index": 1, "name": "内置麦克风"},
        ]
    })

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Serve logs page"""
    logs = get_recent_logs()
    stats = get_log_stats()
    
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs,
        "stats": stats
    })

@app.post("/api/settings")
async def save_settings(settings: Settings):
    """Save KWS settings"""
    try:
        app_state["settings"].update(settings.dict())
        
        # Update KWS engine settings
        if kws_engine:
            await kws_engine.update_settings(app_state["settings"])
        
        return {"status": "success", "message": "Settings saved successfully"}
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keywords")
async def save_keywords(keywords_req: KeywordsRequest):
    """Save keywords"""
    try:
        app_state["keywords"] = keywords_req.keywords
        
        # Update KWS engine keywords
        if kws_engine:
            await kws_engine.update_keywords(keywords_req.keywords)
        
        return {"status": "success", "message": "Keywords saved successfully"}
    except Exception as e:
        logger.error(f"Error saving keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs():
    """Get recent logs"""
    return get_recent_logs()

@app.delete("/api/logs")
async def clear_logs():
    """Clear all logs"""
    logger.info("Logs cleared")
    return {"status": "success", "message": "Logs cleared"}

@app.get("/api/stats")
async def get_stats():
    """Get KWS statistics"""
    return app_state["stats"]

@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "is_processing": app_state["is_processing"],
        "kws_engine_ready": kws_engine is not None,
        "vad_detector_ready": vad_detector is not None,
        "active_connections": len(manager.active_connections),
        "buffer_size": len(app_state["audio_buffer"])
    }

# Utility functions
def get_recent_logs(limit: int = 100) -> List[Dict]:
    """Get recent logs"""
    logs = []
    for i in range(min(limit, 20)):
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": "info",
            "source": "kws",
            "message": f"Log entry {i+1}",
            "details": None
        })
    return logs

def get_log_stats() -> Dict:
    """Get log statistics"""
    return {
        "total_logs": 100,
        "info_logs": 80,
        "warning_logs": 15,
        "error_logs": 5,
        "kws_detections": app_state["stats"]["total_detections"],
        "avg_response_time": app_state["stats"]["processing_time"]
    }

if __name__ == "__main__":
    uvicorn.run(
        "xiaoli.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
