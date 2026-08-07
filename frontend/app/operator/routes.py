from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from ..auth.routes import login_required, permission_required
from ..integrations.analysis_api import FastAPIClient

operator_bp = Blueprint("operator", __name__, url_prefix="/operator")

@operator_bp.route("/console")
@login_required
@permission_required("Operator", "Engineer", "Administrator")
def console():
    hw_status = FastAPIClient.get_hardware_status()
    diagnose = FastAPIClient.get_diagnose()
    data_sources = FastAPIClient.get_system_data_sources()
    return render_template("operator/console.html", hw_status=hw_status, diagnose=diagnose, data_sources=data_sources, user=session.get("user"))

@operator_bp.route("/alarms")
@login_required
@permission_required("Operator", "Engineer", "Administrator")
def alarms():
    diagnose = FastAPIClient.get_diagnose()
    return render_template("operator/alarms.html", diagnose=diagnose, user=session.get("user"))

@operator_bp.route("/diagnosis")
@login_required
@permission_required("Operator", "Engineer", "Administrator")
def diagnosis():
    diagnose = FastAPIClient.get_diagnose()
    return render_template("operator/diagnosis.html", diagnose=diagnose, user=session.get("user"))

@operator_bp.route("/cycles")
@login_required
@permission_required("Operator", "Engineer", "Administrator")
def cycles():
    return render_template("operator/cycles.html", user=session.get("user"))

@operator_bp.route("/maintenance")
@login_required
@permission_required("Operator", "Engineer", "Administrator")
def maintenance():
    logs = FastAPIClient.get_maintenance_logs(limit=20)
    return render_template("operator/maintenance.html", logs=logs, user=session.get("user"))

# 同源同域 BFF 代理端點 (解決跨域 CORS 與 IP/Port  mismatch 問題)
@operator_bp.route("/api/v1/system/data_sources")
@login_required
def get_data_sources_proxy():
    res = FastAPIClient.get_system_data_sources()
    return jsonify(res)

@operator_bp.route("/api/v1/system/switch_source", methods=["POST"])
@login_required
def switch_source_proxy():
    data = request.get_json() or {}
    res = FastAPIClient.switch_system_data_source(data)
    return jsonify(res)

@operator_bp.route("/api/v1/maintenance/logs")
@login_required
def get_maintenance_logs_proxy():
    logs = FastAPIClient.get_maintenance_logs(limit=20)
    return jsonify({"logs": logs, "total": len(logs)})

@operator_bp.route("/api/v1/maintenance/submit", methods=["POST"])
@login_required
def submit_maintenance_log_proxy():
    data = request.get_json() or {}
    operator = session.get("user", {}).get("username", "Operator")
    res = FastAPIClient.submit_maintenance_log(data.get("device", ""), data.get("detail", ""), operator)
    return jsonify(res)
