from flask import Blueprint, render_template, session, request, flash, redirect, url_for, jsonify
from ..auth.routes import login_required, permission_required
from ..integrations.analysis_api import FastAPIClient

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/approvals")
@login_required
@permission_required("Administrator")
def approvals():
    shadow_data = FastAPIClient.get_shadow_mode()
    audit_report = FastAPIClient.get_audit_report()
    return render_template("admin/approvals.html", shadow=shadow_data, audit=audit_report, user=session.get("user"))

@admin_bp.route("/users")
@login_required
@permission_required("Administrator")
def users():
    return render_template("admin/users.html", user=session.get("user"))

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
    return render_template("admin/retention.html", user=session.get("user"))

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
