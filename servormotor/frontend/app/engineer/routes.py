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
    scenarios_data = FastAPIClient.get_scenarios()
    return render_template("engineer/scenarios.html", diagnose=diagnose, scenarios=scenarios_data, user=session.get("user"))

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
    page = request.args.get("page", 1, type=int)
    scen_filter = request.args.get("scenario_id")
    level_filter = request.args.get("level", type=int)
    
    events_data = FastAPIClient.get_fallback_events(page=page, limit=15, scenario_id=scen_filter, level=level_filter)
    stats_data = FastAPIClient.get_fallback_stats(scenario_id=scen_filter, hours=24)
    scenarios_data = FastAPIClient.get_scenarios()
    
    return render_template(
        "engineer/fallbacks.html",
        events=events_data.get("events", []),
        total=events_data.get("total", 0),
        page=page,
        limit=15,
        stats=stats_data,
        scenarios=scenarios_data,
        selected_scen=scen_filter,
        selected_level=level_filter,
        user=session.get("user")
    )

@engineer_bp.route("/adjustments", methods=["GET", "POST"])
@login_required
@permission_required("Engineer", "Administrator")
def adjustments():
    selected_scen_id = request.values.get("scenario_id", 1)
    try:
        selected_scen_id = int(selected_scen_id)
    except Exception:
        selected_scen_id = 1

    diagnose = FastAPIClient.get_diagnose(selected_scen_id)
    scenarios_data = FastAPIClient.get_scenarios()

    if request.method == "POST":
        pa01_val = request.form.get("pa01_val", 1000)
        try:
            pa01_val = int(pa01_val)
        except Exception:
            pa01_val = 1000
        op_id = session.get("user", {}).get("operator_id", "Engineer_01")
        res = FastAPIClient.apply_parameters(selected_scen_id, {"PA01": pa01_val}, op_id)
        if res.get("status") == "success":
            flash(f"成功透過 SLMP MC 協議將參數套用至 {res.get('scenario_name', '驅動器')}！", "success")
        else:
            flash(f"參數套用失敗: {res.get('detail')}", "danger")
        return redirect(url_for("engineer.adjustments", scenario_id=selected_scen_id))

    return render_template("engineer/adjustments.html", diagnose=diagnose, scenarios=scenarios_data, selected_scen_id=selected_scen_id, user=session.get("user"))
