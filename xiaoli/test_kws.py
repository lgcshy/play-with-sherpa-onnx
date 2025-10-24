#!/usr/bin/env python3
"""
Simple test for KWS engine initialization
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_kws_engine():
    """Test KWS engine initialization"""
    print("Testing KWS engine initialization...")
    
    try:
        from xiaoli.kws import KWSEngine
        
        # Test with correct paths
        model_path = "xiaoli/model_data/kws"
        keywords_file = "xiaoli/model_data/kws/text/keyword_token.txt"
        
        print(f"Model path: {model_path}")
        print(f"Keywords file: {keywords_file}")
        
        # Check if files exist
        if not os.path.exists(model_path):
            print(f"Model path does not exist: {model_path}")
            return False
            
        if not os.path.exists(keywords_file):
            print(f"Keywords file does not exist: {keywords_file}")
            return False
        
        # Initialize engine
        print("Initializing KWS engine...")
        engine = KWSEngine(model_path=model_path, keywords_file=keywords_file)
        
        print(f"Engine initialized: {engine.is_initialized}")
        print(f"Engine status: {engine.get_status()}")
        
        return True
        
    except Exception as e:
        print(f"Error initializing KWS engine: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_kws_engine()
    if success:
        print("✅ KWS engine test passed")
    else:
        print("❌ KWS engine test failed")
