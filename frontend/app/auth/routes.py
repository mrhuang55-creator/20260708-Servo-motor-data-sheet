from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from ..integrations.analysis_api import FastAPIClient

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(*allowed_roles):
    """三角色 RBAC 裝飾器（Administrator 具備最高全權限）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("auth.login"))
            user_role = session["user"].get("role")
            # Administrator 自動擁有系統內所有功能之存取權限
            if user_role == "Administrator" or user_role in allowed_roles:
                return f(*args, **kwargs)
            flash(f"權限不足！此功能僅限以下角色存取: {', '.join(allowed_roles)}", "danger")
            return render_template("403.html", user=session.get("user")), 403
        return decorated_function
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        res = FastAPIClient.login(username, password)
        if "error" in res:
            flash(res["error"], "danger")
            return render_template("auth/login.html")
        
        session["user"] = {
            "username": res.get("username"),
            "role": res.get("role"),
            "operator_id": res.get("operator_id"),
            "token": res.get("token")
        }
        
        role = res.get("role")
        if role == "Administrator":
            return redirect(url_for("admin.approvals"))
        elif role == "Engineer":
            return redirect(url_for("engineer.health"))
        else:
            return redirect(url_for("operator.console"))
            
    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("已成功登出系統", "info")
    return redirect(url_for("auth.login"))
