from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from ..auth.routes import login_required, permission_required
from ..integrations.analysis_api import FastAPIClient

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# 資料保留政策：集中於後端定義，避免與前端頁面顯示的天數各自寫死、政策異動時忘記同步
RETENTION_POLICY = {
    "telemetry_days": 30,
    "telemetry_note": "Parquet 壓縮",
    "audit_years": 7,
    "audit_note": "ISO 55000 / 13374 合規永久儲存"
}

@admin_bp.route("/approvals", methods=["GET", "POST"])
@login_required
@permission_required("Administrator")
def approvals():
    if request.method == "POST":
        item_id = request.form.get("item_id")
        action = request.form.get("action")  # approve or reject
        operator = session.get("user", {}).get("username", "Admin_01")
        res = FastAPIClient.process_admin_approval(item_id, action, operator)
        if res.get("status") == "success":
            flash(f"審核操作成功: {res.get('message')}", "success")
        else:
            flash(f"審核操作失敗: {res.get('detail')}", "danger")
        return redirect(url_for("admin.approvals"))

    approvals_data = FastAPIClient.get_admin_approvals()
    shadow_data = FastAPIClient.get_shadow_mode()
    audit_report = FastAPIClient.get_audit_report()
    return render_template("admin/approvals.html", approvals=approvals_data, shadow=shadow_data, audit=audit_report, user=session.get("user"))

@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@permission_required("Administrator")
def users():
    admin_op = session.get("user", {}).get("username", "admin")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            username = request.form.get("username")
            password = request.form.get("password")
            role = request.form.get("role")
            operator_id = request.form.get("operator_id")
            res = FastAPIClient.create_admin_user(username, password, role, operator_id, admin_op)
            if res.get("status") == "success":
                flash(res.get("message", "成功新增員工"), "success")
            else:
                flash(res.get("detail", "新增失敗"), "danger")
                
        elif action == "update":
            user_id = request.form.get("user_id")
            username = request.form.get("username")
            role = request.form.get("role")
            operator_id = request.form.get("operator_id")
            new_password = request.form.get("new_password") or None
            res = FastAPIClient.update_admin_user(user_id, username, role, operator_id, new_password, admin_op)
            if res.get("status") == "success":
                flash(res.get("message", "已更新員工權限資料"), "success")
            else:
                flash(res.get("detail", "更新失敗"), "danger")
                
        elif action == "delete":
            user_id = request.form.get("user_id")
            username = request.form.get("username")
            res = FastAPIClient.delete_admin_user(user_id, username, admin_op)
            if res.get("status") == "success":
                flash(res.get("message", "已刪除員工帳號"), "success")
            else:
                flash(res.get("detail", "刪除失敗"), "danger")
                
        return redirect(url_for("admin.users"))

    users_list = FastAPIClient.get_admin_users()
    audit_logs = FastAPIClient.get_admin_user_history()
    return render_template("admin/users.html", users_list=users_list, audit_logs=audit_logs, user=session.get("user"))

@admin_bp.route("/roles")
@login_required
@permission_required("Administrator")
def roles():
    return render_template("admin/roles.html", user=session.get("user"))

@admin_bp.route("/audit")
@login_required
@permission_required("Administrator")
def audit():
    audit_report = FastAPIClient.get_audit_report()
    return render_template("admin/audit.html", audit=audit_report, user=session.get("user"))

@admin_bp.route("/retention")
@login_required
@permission_required("Administrator")
def retention():
    return render_template("admin/retention.html", retention=RETENTION_POLICY, user=session.get("user"))

@admin_bp.route("/integrations")
@login_required
@permission_required("Administrator")
def integrations():
    hw_status = FastAPIClient.get_hardware_status()
    return render_template("admin/integrations.html", hw_status=hw_status, user=session.get("user"))

@admin_bp.route("/settings")
@login_required
@permission_required("Administrator")
def settings():
    return render_template("admin/settings.html", user=session.get("user"))
