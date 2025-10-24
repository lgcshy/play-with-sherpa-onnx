"""
Voice Activity Detection (VAD) Module
"""

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class VADDetector:
    """Voice Activity Detection using energy-based approach"""
    
    def __init__(self, 
                 energy_threshold: float = 0.01,
                 frame_length: int = 1600,  # 100ms at 16kHz
                 hop_length: int = 800):    # 50ms overlap
        self.energy_threshold = energy_threshold
        self.frame_length = frame_length
        self.hop_length = hop_length
        
        # State for smoothing
        self.energy_history = []
        self.history_length = 10
        
        # Adaptive threshold
        self.noise_level = 0.001
        self.speech_level = 0.01
        self.adaptation_rate = 0.1
    
    def is_speech(self, audio: np.ndarray) -> bool:
        """
        Detect if audio contains speech
        
        Args:
            audio: Audio signal as numpy array
            
        Returns:
            True if speech is detected, False otherwise
        """
        try:
            # Calculate energy
            energy = self.calculate_energy(audio)
            
            # Update noise level (adaptive threshold)
            self.update_noise_level(energy)
            
            # Determine threshold
            threshold = max(self.energy_threshold, self.noise_level * 2)
            
            # Add to history
            self.energy_history.append(energy)
            if len(self.energy_history) > self.history_length:
                self.energy_history.pop(0)
            
            # Check if current energy exceeds threshold
            is_speech = energy > threshold
            
            # Additional checks for speech characteristics
            if is_speech:
                # Check for sudden energy changes (speech onset)
                if len(self.energy_history) >= 3:
                    recent_energies = self.energy_history[-3:]
                    energy_change = max(recent_energies) - min(recent_energies)
                    if energy_change > threshold * 0.5:
                        return True
                
                # Check for sustained energy (speech continuation)
                if len(self.energy_history) >= 5:
                    recent_avg = np.mean(self.energy_history[-5:])
                    if recent_avg > threshold * 0.7:
                        return True
            
            return is_speech
            
        except Exception as e:
            logger.error(f"Error in VAD detection: {e}")
            return False
    
    def calculate_energy(self, audio: np.ndarray) -> float:
        """Calculate RMS energy of audio signal"""
        if len(audio) == 0:
            return 0.0
        
        # Calculate RMS energy
        rms_energy = np.sqrt(np.mean(audio ** 2))
        
        # Apply log scale for better dynamic range
        if rms_energy > 0:
            log_energy = np.log10(rms_energy + 1e-10)
        else:
            log_energy = -10.0
        
        return max(0.0, log_energy + 10.0)  # Normalize to 0-10 range
    
    def update_noise_level(self, energy: float):
        """Update noise level for adaptive threshold"""
        # Simple exponential moving average
        if energy < self.noise_level * 3:  # Likely noise
            self.noise_level = (1 - self.adaptation_rate) * self.noise_level + \
                              self.adaptation_rate * energy
        else:  # Likely speech
            self.noise_level = (1 - self.adaptation_rate * 0.1) * self.noise_level
    
    def reset(self):
        """Reset VAD state"""
        self.energy_history.clear()
        self.noise_level = 0.001
        self.speech_level = 0.01
    
    def get_energy_level(self) -> float:
        """Get current energy level"""
        if self.energy_history:
            return self.energy_history[-1]
        return 0.0
    
    def get_noise_level(self) -> float:
        """Get current noise level"""
        return self.noise_level
    
    def set_threshold(self, threshold: float):
        """Set energy threshold"""
        self.energy_threshold = threshold
        logger.info(f"VAD threshold set to {threshold}")
    
    def get_stats(self) -> dict:
        """Get VAD statistics"""
        return {
            'energy_threshold': self.energy_threshold,
            'noise_level': self.noise_level,
            'current_energy': self.get_energy_level(),
            'history_length': len(self.energy_history)
        }
