import httpx
from flask import current_app

class FastAPIClient:
    """對接 FastAPI (server.py) 分析與診斷後端 API (使用 httpx 連線池與防卡死機制)"""
    
    _client = None

    @classmethod
    def get_client(cls) -> httpx.Client:
        if cls._client is None:
            cls._client = httpx.Client(timeout=5.0)
        return cls._client

    @staticmethod
    def _get_url(endpoint: str) -> str:
        base_url = current_app.config.get("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000")
        return f"{base_url.rstrip('/')}{endpoint}"

    @classmethod
    def login(cls, username: str, password: str):
        url = cls._get_url("/api/v1/auth/login")
        try:
            resp = cls.get_client().post(url, json={"username": username, "password": password})
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.json().get("detail", "登入失敗")}
        except Exception as e:
            return {"error": f"無法連線後端 API: {str(e)}"}

    @classmethod
    def get_hardware_status(cls):
        url = cls._get_url("/api/v1/hardware/status")
        try:
            resp = cls.get_client().get(url)
            return resp.json() if resp.status_code == 200 else {"connected": False, "status": "Error"}
        except Exception:
            return {"connected": False, "status": "後端服務離線"}

    @classmethod
    def get_scenarios(cls):
        url = cls._get_url("/api/v1/scenarios")
        try:
            resp = cls.get_client().get(url)
            if resp.status_code == 200:
                return resp.json().get("scenarios", {})
            return {}
        except Exception:
            return {}

    @classmethod
    def get_diagnose(cls, scenario_id: int = None):
        url = cls._get_url("/api/v1/diagnose")
        params = {"scenario_id": scenario_id} if scenario_id else {}
        try:
            resp = cls.get_client().get(url, params=params)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def get_shadow_mode(cls):
        url = cls._get_url("/api/v1/shadow_mode")
        try:
            resp = cls.get_client().get(url)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def get_admin_approvals(cls):
        url = cls._get_url("/api/v1/admin/approvals")
        try:
            resp = cls.get_client().get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {
            "pending_items": [],
            "counts": {"model_promotion": 0, "scenario_review": 0, "parameter_write": 0, "unauthorized": 0}
        }

    @classmethod
    def process_admin_approval(cls, item_id: str, action: str, operator: str = "Admin_01"):
        url = cls._get_url("/api/v1/admin/approve")
        try:
            resp = cls.get_client().post(url, json={"item_id": item_id, "action": action, "operator": operator})
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "執行失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    def get_audit_report(cls):
        url = cls._get_url("/api/v1/export_audit_report")
        try:
            resp = cls.get_client().get(url)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    @classmethod
    def get_fallback_events(cls, page: int = 1, limit: int = 20, scenario_id: str = None, level: int = None):
        url = cls._get_url("/api/v1/fallback/events")
        params = {"page": page, "limit": limit}
        if scenario_id:
            params["scenario_id"] = scenario_id
        if level:
            params["level"] = level
        try:
            resp = cls.get_client().get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"events": [], "total": 0, "page": page, "limit": limit}

    @classmethod
    def get_fallback_stats(cls, scenario_id: str = None, hours: int = 24):
        url = cls._get_url("/api/v1/fallback/stats")
        params = {"hours": hours}
        if scenario_id:
            params["scenario_id"] = scenario_id
        try:
            resp = cls.get_client().get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"by_reason": {}, "by_level": {}}

    @classmethod
    def apply_parameters(cls, scenario_id: int, parameters: dict, operator_id: str):
        url = cls._get_url("/api/v1/apply_parameters")
        payload = {
            "scenario_id": scenario_id,
            "parameters": parameters,
            "operator_id": operator_id
        }
        try:
            resp = cls.get_client().post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "執行失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    def get_admin_users(cls):
        url = cls._get_url("/api/v1/admin/users")
        try:
            resp = cls.get_client().get(url)
            if resp.status_code == 200:
                return resp.json().get("users", [])
        except Exception:
            pass
        return []

    @classmethod
    def create_admin_user(cls, username, password, role, operator_id=None, admin_operator="admin"):
        url = cls._get_url("/api/v1/admin/users/create")
        payload = {
            "username": username, "password": password,
            "role": role, "operator_id": operator_id, "admin_operator": admin_operator
        }
        try:
            resp = cls.get_client().post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "新增員工失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    def update_admin_user(cls, user_id, username, role, operator_id=None, new_password=None, admin_operator="admin"):
        url = cls._get_url("/api/v1/admin/users/update")
        payload = {
            "user_id": int(user_id), "username": username, "role": role,
            "operator_id": operator_id, "new_password": new_password, "admin_operator": admin_operator
        }
        try:
            resp = cls.get_client().post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "更新員工資料失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    def delete_admin_user(cls, user_id, username, admin_operator="admin"):
        url = cls._get_url("/api/v1/admin/users/delete")
        payload = {"user_id": int(user_id), "username": username, "admin_operator": admin_operator}
        try:
            resp = cls.get_client().post(url, json=payload)
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "detail": resp.json().get("detail", "刪除員工失敗")}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    @classmethod
    def get_admin_user_history(cls):
        url = cls._get_url("/api/v1/admin/users/history")
        try:
            resp = cls.get_client().get(url)
            if resp.status_code == 200:
                return resp.json().get("logs", [])
        except Exception:
            pass
        return []
