#!/usr/bin/env python3
"""
AI SERVO PLATFORM 一鍵啟動器 (Launcher for Executable Packaging)
同時啟動 FastAPI 分析後端 (Port 8000) 與 Flask 前端 BFF (Port 5000)，並自動開啟瀏覽器。
防閃退與資源定位優化版
"""
import os
import sys
import time
import threading
import webbrowser
import multiprocessing
import uvicorn

# 防範 PyInstaller 子進程無限自我複製閃退
multiprocessing.freeze_support()

# 取得 PyInstaller 解壓或本地根目錄
if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import app as fastapi_app
from frontend.app import create_app as create_flask_app

def run_fastapi():
    print("[AI SERVO PLATFORM] 啟動 FastAPI 分析後端 (Port 8000)...")
    try:
        uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")
    except Exception as e:
        print(f"[警告] FastAPI 後端啟動失敗: {e}")

def run_flask():
    print("[AI SERVO PLATFORM] 啟動 Flask 前端 BFF (Port 5000)...")
    try:
        flask_app = create_flask_app()
        flask_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[警告] Flask 前端啟動失敗: {e}")

def open_browser():
    time.sleep(2.5)
    print("[AI SERVO PLATFORM] 自動開啟系統畫面: http://127.0.0.1:5000")
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("  三菱 MR-J5 伺服馬達 AI 智慧健康診斷與預測維護系統")
        print("  AI SERVO PLATFORM v7.1.0 Executable Launcher (全 41 工況對齊版)")
        print("=" * 60)

        # 啟動 FastAPI 線程
        t_fastapi = threading.Thread(target=run_fastapi, daemon=True)
        t_fastapi.start()

        # 啟動自動開啟瀏覽器線程
        t_browser = threading.Thread(target=open_browser, daemon=True)
        t_browser.start()

        # 啟動 Flask 主線程
        run_flask()
    except Exception as e:
        print(f"\n[致命錯誤] 系統啟動發生異常: {e}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 鍵結束...")
