#!/usr/bin/env python3
import argparse, json
from pathlib import Path

RULES = {
    "following_error": [
        ["Position loop gain", "Feedforward", "Model adaptive control", "Positioning completion range"],
        "Increase response gradually; verify overshoot and settling.",
        ["following_error_abs_pulse", "settling_time_ms", "in_position_rate"]
    ],
    "thermal": [
        ["Acceleration/deceleration time constant", "Torque limit", "Current limit", "Duty profile"],
        "Reduce thermal stress while maintaining takt time.",
        ["motor_temp_c", "drive_temp_c", "current_rms_a"]
    ],
    "vibration": [
        ["Advanced vibration suppression control II", "Machine resonance suppression filter", "Command notch filter", "Robust filter"],
        "Identify resonance frequency and set suppression / notch filter.",
        ["vibration_rms_g", "fft_1x_amp", "resonance_amp"]
    ],
    "bearing": [
        ["Machine diagnosis", "Speed limit", "Acceleration limit", "Vibration suppression"],
        "Reduce mechanical stress and raise predictive-maintenance priority.",
        ["bearing_bpfo_amp", "bearing_bpfi_amp", "bearing_health_index", "rul_sec"]
    ],
    "torque_ripple": [
        ["Torque filter", "Command notch filter", "Gain tuning"],
        "Filter ripple frequency and verify current/torque response.",
        ["torque_error_nm", "current_rms_a", "fft_2x_amp"]
    ],
    "current_load": [
        ["Torque limit", "Current limit", "Load inertia ratio", "Acceleration/deceleration"],
        "Retune load inertia and reduce peak current.",
        ["current_rms_a", "torque_limit_pct", "cycle_time_ms"]
    ],
    "network": [
        ["PLC motion command cycle", "CC-Link IE TSN / EtherCAT sync", "Command smoothing"],
        "Stabilize command timing and reduce jitter.",
        ["network_jitter_ms", "ethercat_sync_error_us", "packet_loss_pct"]
    ],
    "digital_twin_error": [
        ["Digital twin model update", "Feedforward", "Friction compensation", "Lost motion compensation"],
        "Update model and compensate physical tracking error.",
        ["digital_twin_pos_residual", "digital_twin_speed_residual", "position_error_pulse"]
    ],
    # --- 以下為 PART 5 新增的進階故障場景優化規則 ---
    "communication_loss_of_control": [
        ["PLC motion command cycle", "CC-Link IE TSN / EtherCAT sync", "Command smoothing"],
        "Suppress network package loss and scan jitter first; do not tune gains.",
        ["ethercat_packet_loss_pct", "plc_scan_time_ms_anomaly", "ethercat_sync_error_us"]
    ],
    "gain_instability": [
        ["Speed gain", "Position Gain", "Robust filter", "Speed integral time constant"],
        "Reduce aggressive gain levels or enable robust filter to avoid loop oscillation.",
        ["following_error_abs_pulse", "frequency_response_100hz_db", "vibration_rms_g"]
    ],
    "resonance": [
        ["Machine resonance suppression filter", "Command notch filter", "Vibration suppression control"],
        "Apply notch filters to suppress mechanical resonance peak (>100Hz).",
        ["vibration_rms_g", "frequency_response_100hz_db", "torque_error_nm"]
    ],
    "brake_failure": [
        ["Brake release delay time", "Brake hold delay time", "Vertical axis torque compensation"],
        "Verify brake status and adjust mechanical brake timing constants to prevent vertical shaft slip.",
        ["digital_twin_pos_residual", "torque_error_nm", "following_error_abs_pulse"]
    ],
    "emergency_stop": [
        ["Forced stop deceleration time constant", "Emergency stop torque limit", "Deceleration smoothing"],
        "Check safety circuits and adjust deceleration ramp time constants to prevent mechanical shock during E-stops.",
        ["plc_estop_active", "following_error_abs_pulse", "torque_limit_pct"]
    ],
    "combined_fault": [
        ["CC-Link IE TSN / EtherCAT sync", "Load inertia ratio", "Acceleration/deceleration time constant", "Torque limit"],
        "Address combined thermal and communication jitter. Cross-correlation shows network coupling.",
        ["ethercat_packet_loss_pct", "motor_temp_c", "torque_error_nm", "vibration_rms_g"]
    ],
    "progressive_failure": [
        ["Machine diagnosis threshold", "Speed limit", "Acceleration limit", "Maintenance schedule"],
        "Track progressive degradation and schedule preventive maintenance to prevent shutdown.",
        ["health_index", "rul_sec", "bearing_bpfo_amp", "bearing_bpfi_amp"]
    ],
    # --- 以下為 新增的 01-06 故障/健康場景優化規則 ---
    "normal": [
        [],
        "No adjustment needed. System is operating normally.",
        []
    ],
    "motor_over_temp": [
        ["Acceleration/deceleration time constant", "Torque limit", "Current limit"],
        "Reduce motor acceleration/deceleration rate and duty cycle to prevent thermal run-away.",
        ["motor_temp_c", "current_rms_a"]
    ],
    "drive_over_temp": [
        ["Acceleration/deceleration time constant", "Torque limit", "Current limit"],
        "Reduce motor peak current and increase deceleration time constant to prevent drive thermal trip.",
        ["drive_temp_c", "current_rms_a"]
    ],
    "encoder_drift": [
        ["Lost motion compensation", "Feed-forward", "In-position range"],
        "Compensate for mechanical offset and adjust lost motion/backlash compensation values.",
        ["digital_twin_pos_residual", "encoder_drift_pulse"]
    ],
    "encoder_noise": [
        ["Current filter", "Command notch filter", "Following error limit"],
        "Enable command filter / smoothing to filter out high-frequency encoder feedback noise.",
        ["following_error_abs_pulse", "encoder_error_count"]
    ],
    "encoder_signal_loss": [
        ["Forced stop decel", "Brake timing", "Following error limit"],
        "Encoder signal loss detected! Trigger immediate emergency deceleration stop and engage brakes.",
        ["encoder_error_count", "health_index"]
    ]
}

def optimize(ai):
    root = ai.get("root_cause", "following_error")
    groups, action, kpi = RULES.get(root, RULES["following_error"])
    
    writes = {}
    
    # 1. 共振抑制 Notch Filter 寫入
    peak = ai.get("fft_resonance_peak")
    if peak and float(peak) > 0:
        writes["PA18"] = int(round(peak))
        writes["PB12"] = int(round(peak * 1.5))
        
    # 2. 遺失運動與反向間隙補償 (Lost Motion Compensation) -> S04 漂移
    if root == "encoder_drift" or "encoder_drift" in root:
        drift = ai.get("encoder_drift_pulse", 120.0)
        writes["PE07"] = int(round(drift * 0.8)) # 補償 80% 穩態間隙
        
    # 3. 摩擦力補償 (Friction Compensation) -> 軸承磨損與卡阻
    if root == "bearing" or ai.get("friction_estimate_nm", 0.0) > 0:
        friction = ai.get("friction_estimate_nm", 1.5)
        writes["PE02"] = int(round(friction * 100.0)) # 轉換為對應參數單位
        
    return {
        "ai_root_cause": root,
        "confidence": ai.get("confidence", 0),
        "mr_j5_parameter_group": groups,
        "recommended_action": action,
        "trial_plan": ["Read parameters", "Set trial parameters", "Low-speed trial", "Production-speed trial", "Collect after data", "Compare KPI", "Save parameters"],
        "mr_j5_parameter_writes": writes,
        "target_kpi": kpi,
        "save_condition": "Save when KPI improvement >= 10% and no new alarm/trip is detected."
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ai_result", required=True)
    p.add_argument("--out", default="optimizer_recommendation.json")
    a = p.parse_args()
    rec = optimize(json.loads(Path(a.ai_result).read_text(encoding="utf-8")))
    Path(a.out).write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rec, indent=2, ensure_ascii=False))
