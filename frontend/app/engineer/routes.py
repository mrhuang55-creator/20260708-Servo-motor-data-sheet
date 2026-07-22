from flask import Blueprint, render_template, session, request, flash, redirect, url_for
from ..auth.routes import login_required, permission_required
from ..integrations.analysis_api import FastAPIClient

engineer_bp = Blueprint("engineer", __name__, url_prefix="/engineer")

@engineer_bp.route("/health")
@login_required
@permission_required("Engineer", "Administrator")
def health():
    hw_status = FastAPIClient.get_hardware_status()
    shadow_data = FastAPIClient.get_shadow_mode()
    diagnose = FastAPIClient.get_diagnose()
    return render_template("engineer/health.html", hw_status=hw_status, shadow=shadow_data, diagnose=diagnose, user=session.get("user"))

@engineer_bp.route("/features")
@login_required
@permission_required("Engineer", "Administrator")
def features():
    return render_template("engineer/features.html", user=session.get("user"))

@engineer_bp.route("/scenarios")
@login_required
@permission_required("Engineer", "Administrator")
def scenarios():
    diagnose = FastAPIClient.get_diagnose()
    return render_template("engineer/scenarios.html", diagnose=diagnose, user=session.get("user"))

@engineer_bp.route("/models")
@login_required
@permission_required("Engineer", "Administrator")
def models():
    shadow_data = FastAPIClient.get_shadow_mode()
    return render_template("engineer/models.html", shadow=shadow_data, user=session.get("user"))

@engineer_bp.route("/shadow")
@login_required
@permission_required("Engineer", "Administrator")
def shadow():
    shadow_data = FastAPIClient.get_shadow_mode()
    return render_template("engineer/shadow.html", shadow=shadow_data, user=session.get("user"))

@engineer_bp.route("/fallbacks")
@login_required
@permission_required("Engineer", "Administrator")
def fallbacks():
    return render_template("engineer/fallbacks.html", user=session.get("user"))

@engineer_bp.route("/adjustments", methods=["GET", "POST"])
@login_required
@permission_required("Engineer", "Administrator")
def adjustments():
    diagnose = FastAPIClient.get_diagnose()
    if request.method == "POST":
        scenario_id = int(request.form.get("scenario_id", 1))
        # 簡單參數寫入測試
        op_id = session.get("user", {}).get("operator_id", "Engineer_01")
        res = FastAPIClient.apply_parameters(scenario_id, {"PA01": 1000}, op_id)
        if res.get("status") == "success":
            flash("成功透過 SLMP MC 協議將參數套用至驅動器！", "success")
        else:
            flash(f"參數套用失敗: {res.get('detail')}", "danger")
        return redirect(url_for("engineer.adjustments"))

    return render_template("engineer/adjustments.html", diagnose=diagnose, user=session.get("user"))
