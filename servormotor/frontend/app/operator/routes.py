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
    return render_template("operator/console.html", hw_status=hw_status, diagnose=diagnose, user=session.get("user"))

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
    return render_template("operator/maintenance.html", user=session.get("user"))
