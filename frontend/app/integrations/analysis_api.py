import requests
from flask import current_app

class FastAPIClient:
    """對接 FastAPI (server.py) 分析與診斷後端 API"""
    
    @staticmethod
    def _get_url(endpoint: str) -> str:
        base_url = current_app.config.get("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000")
        return f"{base_url.rstrip('/')}{endpoint}"

    @classmethod
    def login(cls, username: str, password: str):
        url = cls._get_url("/api/v1/auth/login")
        try:
            resp = requests.post(url, json={"username": username, "password": password}, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.json().get("detail", "登入失敗")}
        except Exception as e:
            return {"error": f"無法連線後端 API: {str(e)}"}

    @classmethod
    def get_hardware_status(cls):
        url = cls._get_url("/api/v1/hardware/status")
        try:
            resp = requests.get(url, timeout=3)
            return resp.json() if resp.status_code == 200 else {"connected": False, "status": "Error"}
        except Exception:
            return {"connected": False, "status": "後端服務離線"}

    @classmethod
    def get_diagnose(cls, scenario_id: int = None):
        url = cls._get_url("/api/v1/diagnose")
        params = {"scenario_id": scenario_id} if scenario_id else {}
        try:
            resp = requests.get(url, params=params, timeout=5)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def get_shadow_mode(cls):
        url = cls._get_url("/api/v1/shadow_mode")
        try:
            resp = requests.get(url, timeout=3)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def get_audit_report(cls):
        url = cls._get_url("/api/v1/export_audit_report")
        try:
            resp = requests.get(url, timeout=5)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def apply_parameters(cls, scenario_id: int, parameters: dict, operator_id: str):
        url = cls._get_url("/api/v1/apply_parameters")
        payload = {
            "scenario_id": scenario_id,
            "parameters": parameters,
            "operator_id": operator_id
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "執行失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
