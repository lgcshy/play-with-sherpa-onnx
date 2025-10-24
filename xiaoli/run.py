#!/usr/bin/env python3
"""
Xiaoli KWS FastAPI Application Launcher
"""

import sys
import os
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point"""
    print("Starting Xiaoli KWS FastAPI Application...")
    print("=" * 50)
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "true").lower() == "true"  # Enable debug by default
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Reload: {reload}")
    print("=" * 50)
    
    # Run the application
    uvicorn.run(
        "xiaoli.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info" if not debug else "debug",
        access_log=True
    )

if __name__ == "__main__":
    main()
