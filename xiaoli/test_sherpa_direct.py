#!/usr/bin/env python3
"""
Test sherpa-onnx keyword spotter directly
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_sherpa_onnx_direct():
    """Test sherpa-onnx keyword spotter directly"""
    try:
        import sherpa_onnx
        
        # Initialize keyword spotter
        kws = sherpa_onnx.keyword_spotter.KeywordSpotter(
            tokens="xiaoli/model_data/kws/tokens.txt",
            encoder="xiaoli/model_data/kws/encoder-epoch-12-avg-2-chunk-16-left-64.onnx",
            decoder="xiaoli/model_data/kws/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
            joiner="xiaoli/model_data/kws/joiner-epoch-12-avg-2-chunk-16-left-64.onnx",
            keywords_file="xiaoli/model_data/kws/text/keyword_token.txt",
            num_threads=2,
            provider="cpu",
            max_active_paths=4,
            num_trailing_blanks=1,
            keywords_score=1.0,
            keywords_threshold=0.25,
        )
        
        print("✅ KWS initialized successfully")
        
        # Create stream
        stream = kws.create_stream()
        print("✅ Stream created successfully")
        
        # Test with different audio sizes
        test_sizes = [100, 500, 1000, 1600, 3200]
        
        for size in test_sizes:
            print(f"\nTesting with {size} samples:")
            
            # Generate test audio
            audio = np.random.randn(size).astype(np.float32) * 0.1
            
            try:
                # Accept waveform
                stream.accept_waveform(sample_rate=16000, waveform=audio)
                print(f"  ✅ Accepted waveform: {size} samples")
                
                # Decode stream
                kws.decode_stream(stream)
                print(f"  ✅ Decoded stream: {size} samples")
                
                # Check if ready
                is_ready = kws.is_ready(stream)
                print(f"  ✅ Is ready: {is_ready}")
                
                if is_ready:
                    result = kws.get_result(stream)
                    print(f"  ✅ Result: {result}")
                
            except Exception as e:
                print(f"  ❌ Error with {size} samples: {e}")
                break
        
        print("\n✅ Direct sherpa-onnx test completed")
        
    except Exception as e:
        print(f"❌ Direct sherpa-onnx test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sherpa_onnx_direct()
