#!/usr/bin/env python3
"""
启动脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("DEBUG", "true")

# 导入并运行服务器
from backend.main import run_server

if __name__ == "__main__":
    run_server()
