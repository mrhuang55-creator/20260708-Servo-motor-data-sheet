import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ai-servo-phm-flask-secret-key-2026")
    FASTAPI_BACKEND_URL = os.environ.get("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000")
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # 開發環境改為 False，正式環境設 True
    SESSION_COOKIE_SAMESITE = "Lax"
