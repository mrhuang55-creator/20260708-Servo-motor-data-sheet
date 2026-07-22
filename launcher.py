#!/usr/bin/env python3
"""
AI SERVO PLATFORM 一鍵啟動器 (Launcher for Executable Packaging)
同時啟動 FastAPI 分析後端 (Port 8000) 與 Flask 前端 BFF (Port 5000)，並自動開啟瀏覽器。
"""
import os
import sys
import time
import threading
import webbrowser
import uvicorn

# 將目前目錄加入 sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from server import app as fastapi_app
from frontend.app import create_app as create_flask_app

def run_fastapi():
    print("[AI SERVO PLATFORM] 啟動 FastAPI 分析後端 (Port 8000)...")
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")

def run_flask():
    print("[AI SERVO PLATFORM] 啟動 Flask 前端 BFF (Port 5000)...")
    flask_app = create_flask_app()
    flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def open_browser():
    time.sleep(2)
    print("[AI SERVO PLATFORM] 自動開啟系統畫面: http://127.0.0.1:5000")
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    print("=" * 60)
    print("  三菱 MR-J5 伺服馬達 AI 智慧健康診斷與預測維護系統")
    print("  AI SERVO PLATFORM v6.5.0 Executable Launcher")
    print("=" * 60)

    # 啟動 FastAPI 線程
    t_fastapi = threading.Thread(target=run_fastapi, daemon=True)
    t_fastapi.start()

    # 啟動自動開啟瀏覽器線程
    t_browser = threading.Thread(target=open_browser, daemon=True)
    t_browser.start()

    # 啟動 Flask 主線程
    run_flask()
