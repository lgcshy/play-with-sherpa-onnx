"""
Keyword Spotting Engine with streaming support
"""

import sherpa_onnx
import numpy as np
import logging
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)

class KWSEngine:
    """Keyword Spotting Engine with streaming capabilities"""
    
    def __init__(self, 
                 model_path: str = "xiaoli/model_data/kws",
                 keywords_file: str = "xiaoli/model_data/kws/text/keyword_token.txt"):
        self.model_path = model_path
        self.keywords_file = keywords_file
        self.kws = None
        self.current_stream = None
        self.is_initialized = False
        
        # Audio accumulation buffer
        self.audio_buffer = []
        self.min_audio_length = 16000  # 1 second at 16kHz
        
        # Default settings
        self.settings = {
            "threshold": 0.25,
            "score": 1.0,
            "max_active_paths": 4,
            "num_trailing_blanks": 1,
            "num_threads": 2,
            "provider": "cpu"
        }
        
        # Initialize the engine
        self._initialize()
    
    def _initialize(self):
        """Initialize the KWS engine"""
        try:
            # Check if model files exist
            if not self._check_model_files():
                raise FileNotFoundError("KWS model files not found")
            
            # Initialize sherpa-onnx keyword spotter
            self.kws = sherpa_onnx.keyword_spotter.KeywordSpotter(
                tokens=os.path.join(self.model_path, "tokens.txt"),
                encoder=os.path.join(self.model_path, "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
                decoder=os.path.join(self.model_path, "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
                joiner=os.path.join(self.model_path, "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"),
                keywords_file=self.keywords_file,
                num_threads=self.settings["num_threads"],
                provider=self.settings["provider"],
                max_active_paths=self.settings["max_active_paths"],
                num_trailing_blanks=self.settings["num_trailing_blanks"],
                keywords_score=self.settings["score"],
                keywords_threshold=self.settings["threshold"],
            )
            
            self.is_initialized = True
            logger.info("KWS engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing KWS engine: {e}")
            self.is_initialized = False
            raise
    
    def _check_model_files(self) -> bool:
        """Check if all required model files exist"""
        required_files = [
            "tokens.txt",
            "encoder-epoch-12-avg-2-chunk-16-left-64.onnx",
            "decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
            "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"
        ]
        
        for file in required_files:
            file_path = os.path.join(self.model_path, file)
            if not os.path.exists(file_path):
                logger.error(f"Model file not found: {file_path}")
                return False
        
        return True
    
    async def stream_detect(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Process audio chunk for keyword detection using accumulation
        
        Args:
            audio_chunk: Audio data as numpy array (float32, normalized)
            
        Returns:
            Detection result dict or None
        """
        if not self.is_initialized or self.kws is None:
            logger.warning("KWS engine not initialized")
            return None
        
        try:
            # Ensure audio is in correct format
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)
            
            # Ensure audio is normalized
            if np.max(np.abs(audio_chunk)) > 1.0:
                audio_chunk = audio_chunk / np.max(np.abs(audio_chunk))
            
            # Add to accumulation buffer
            self.audio_buffer.extend(audio_chunk.tolist())
            
            # Only process when we have enough audio
            if len(self.audio_buffer) < self.min_audio_length:
                logger.debug(f"Accumulating audio: {len(self.audio_buffer)}/{self.min_audio_length} samples")
                return None
            
            # Create stream if not exists
            if self.current_stream is None:
                self.current_stream = self.kws.create_stream()
            
            # Convert buffer to numpy array
            accumulated_audio = np.array(self.audio_buffer, dtype=np.float32)
            
            # Feed accumulated audio data to stream
            self.current_stream.accept_waveform(
                sample_rate=16000,
                waveform=accumulated_audio
            )
            
            # Decode stream
            self.kws.decode_stream(self.current_stream)
            
            # Check if keyword is detected
            if self.kws.is_ready(self.current_stream):
                keyword = self.kws.get_result(self.current_stream)
                if keyword and keyword.strip():
                    # Reset stream and buffer for next detection
                    self.kws.reset_stream(self.current_stream)
                    self.current_stream = None
                    self.audio_buffer = []
                    
                    return {
                        "keyword": keyword.strip(),
                        "confidence": 0.8,  # Default confidence, sherpa-onnx doesn't provide this directly
                        "timestamp": None  # Will be set by caller
                    }
            
            # Keep only recent audio in buffer (sliding window)
            if len(self.audio_buffer) > self.min_audio_length * 2:
                self.audio_buffer = self.audio_buffer[-self.min_audio_length:]
            
            return None
            
        except Exception as e:
            logger.error(f"Error in KWS detection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def update_settings(self, new_settings: Dict[str, Any]):
        """Update KWS engine settings"""
        try:
            # Update settings
            self.settings.update(new_settings)
            
            # Reinitialize engine with new settings
            self._initialize()
            
            logger.info("KWS settings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating KWS settings: {e}")
            raise
    
    async def update_keywords(self, keywords: List[str]):
        """Update keywords list"""
        try:
            # Save keywords to file
            with open(self.keywords_file, 'w', encoding='utf-8') as f:
                for keyword in keywords:
                    f.write(f"{keyword}\n")
            
            # Reinitialize engine to load new keywords
            self._initialize()
            
            logger.info(f"Keywords updated: {keywords}")
            
        except Exception as e:
            logger.error(f"Error updating keywords: {e}")
            raise
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        return self.settings.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "is_initialized": self.is_initialized,
            "model_path": self.model_path,
            "keywords_file": self.keywords_file,
            "settings": self.settings
        }
    
    def reset(self):
        """Reset the engine"""
        self.kws = None
        self.current_stream = None
        self.is_initialized = False
        self._initialize()
    
    def reset_stream(self):
        """Reset current stream and audio buffer"""
        if self.current_stream and self.kws:
            self.kws.reset_stream(self.current_stream)
        self.current_stream = None
        self.audio_buffer = []

# Global KWS engine instance
kws_engine = KWSEngine()

# Legacy compatibility
kws = kws_engine.kws if kws_engine.is_initialized else None