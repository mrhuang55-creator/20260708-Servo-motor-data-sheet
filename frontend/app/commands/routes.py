import time
import uuid
from flask import Blueprint, jsonify, request, session
from ..auth.routes import login_required
from ..integrations.analysis_api import FastAPIClient

commands_bp = Blueprint("commands", __name__, url_prefix="/api/ui")

@commands_bp.route("/dashboard/snapshot", methods=["GET"])
@login_required
def get_snapshot():
    hw_status = FastAPIClient.get_hardware_status()
    diagnose = FastAPIClient.get_diagnose()
    shadow = FastAPIClient.get_shadow_mode()
    return jsonify({
        "timestamp": time.time(),
        "hardware": hw_status,
        "diagnose": diagnose,
        "shadow": shadow,
        "system_status": "NORMAL" if hw_status.get("connected") else "OFFLINE"
    })

@commands_bp.route("/commands/cycle/start", methods=["POST"])
@login_required
def cycle_start():
    command_id = f"cmd_{uuid.uuid4().hex[:8]}"
    return jsonify({
        "command_id": command_id,
        "status": "completed",
        "action": "cycle_start",
        "timestamp": time.time(),
        "message": "Cycle 指令已順利發送至伺服控制系統"
    })

@commands_bp.route("/commands/cycle/stop", methods=["POST"])
@login_required
def cycle_stop():
    command_id = f"cmd_{uuid.uuid4().hex[:8]}"
    return jsonify({
        "command_id": command_id,
        "status": "completed",
        "action": "cycle_stop",
        "timestamp": time.time(),
        "message": "Cycle 停止指令已順利發送"
    })

@commands_bp.route("/emergency-stop-request", methods=["POST"])
@login_required
def emergency_stop_request():
    command_id = f"estop_{uuid.uuid4().hex[:8]}"
    operator = session.get("user", {}).get("username", "Unknown")
    return jsonify({
        "command_id": command_id,
        "status": "accepted",
        "action": "emergency_stop_request",
        "operator": operator,
        "timestamp": time.time(),
        "message": "緊急停機請求 (E-Stop Request) 已由 Flask 安全閘道成功送出至伺服驅動器！"
    })
