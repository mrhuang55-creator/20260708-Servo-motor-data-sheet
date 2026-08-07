#!/usr/bin/env python3
import os
import sys

# 將專案根目錄納入 Python Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("[AI SERVO PLATFORM] Flask 前端 BFF 服務啟動中 (Port 5000)...")
    app.run(host="0.0.0.0", port=5000, debug=False)
