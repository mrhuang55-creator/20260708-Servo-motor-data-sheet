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
    ],
    # --- 以下為 新增的 07-22 & 24 優化規則 ---
    "coupling_misalignment": [
        ["Speed gain", "Robust filter", "Position Gain"],
        "Reduce speed loop gain slightly to suppress misalignment oscillation.",
        ["vibration_rms_g", "fft_1x_amp"]
    ],
    "belt_slack": [
        ["Position Loop Gain", "Acceleration/deceleration time constant", "Command filter"],
        "Decrease position loop gain to avoid belt elasticity oscillation.",
        ["following_error_abs_pulse", "vibration_rms_g"]
    ],
    "gearbox_backlash": [
        ["Lost motion compensation", "Backlash compensation"],
        "Increase lost motion compensation value (PE07) to adjust backlash.",
        ["digital_twin_pos_residual", "encoder_drift_pulse"]
    ],
    "ball_screw_friction": [
        ["Friction compensation", "Torque limit"],
        "Increase friction compensation (PE02) to compensate for wear.",
        ["torque_error_nm", "current_rms_a", "motor_temp_c"]
    ],
    "phase_loss": [
        ["Torque limit", "Current limit"],
        "Limit motor torque and current, prompt phase loss wire inspection.",
        ["current_unbalance_pct", "motor_temp_c"]
    ],
    "bus_overvoltage": [
        ["Deceleration time constant", "Torque limit"],
        "Increase deceleration time constant to reduce peak regenerative voltage.",
        ["drive_temp_c", "torque_error_nm"]
    ],
    "bus_undervoltage": [
        ["Acceleration time constant", "Torque limit"],
        "Increase acceleration time constant to reduce instantaneous load current.",
        ["following_error_abs_pulse", "current_rms_a"]
    ],
    "mechanical_jam": [
        ["Torque limit", "Forced stop deceleration"],
        "Decrease torque limit to protect mechanical parts, prompt inspection.",
        ["torque_error_nm", "following_error_abs_pulse"]
    ],
    "fan_failure": [
        ["None"],
        "Reduce duty cycle, schedule fan maintenance.",
        ["drive_temp_c", "current_rms_a"]
    ],
    "ground_noise": [
        ["Current filter", "Command filter"],
        "Increase current filter time constant (PB18) to smooth noise.",
        ["encoder_error_count", "following_error_abs_pulse"]
    ],
    "limit_active": [
        ["Forced stop deceleration", "Brake timing"],
        "Immediate emergency braking and engage mechanical holding brakes.",
        ["plc_estop_active", "brake_status_bool"]
    ],
    "accel_aggressive": [
        ["Acceleration/deceleration time constant", "Command filter"],
        "Increase acceleration/deceleration time constant to smooth profile.",
        ["current_rms_a", "following_error_abs_pulse"]
    ],
    "dynamic_brake_fail": [
        ["Brake delay timing", "Forced stop deceleration"],
        "Adjust brake delay to reduce mechanical slip distance.",
        ["following_error_abs_pulse", "vibration_rms_g"]
    ],
    "command_jitter": [
        ["Command filter", "Command smoothing"],
        "Increase command smoothing filter (PB18) to filter step commands.",
        ["network_jitter_ms", "following_error_abs_pulse"]
    ],
    "inertia_mismatch": [
        ["Load inertia ratio", "Auto tuning"],
        "Retune load inertia ratio (PA09) to match payload.",
        ["following_error_abs_pulse", "vibration_rms_g"]
    ],
    "bearing_wear": [
        ["Friction compensation", "Vibration suppression"],
        "Apply bearing friction compensation (PE02), monitor BPFO/BPFI.",
        ["bearing_bpfo_amp", "bearing_bpfi_amp", "health_index"]
    ],
    "sync_timeout": [
        ["None"],
        "Inspect TSN/EtherCAT master sync cycle, bypass servo gains tuning.",
        ["ethercat_sync_error_us", "network_jitter_ms"]
    ]
}

def optimize(ai):
    root = ai.get("root_cause", "following_error")
    groups, action, kpi = RULES.get(root, RULES["following_error"])
    
    writes = {}
    
    # 讀取當前參數
    current_params = ai.get("current_parameters", {
        "PB07": 100, # Position loop gain
        "PB08": 150, # Speed loop gain
        "PB09": 20,  # Speed integral time constant
        "PA09": 12,  # Auto tuning response level
        "PA11": 300, # Forward torque limit
        "PA12": 300, # Reverse torque limit
        "PC16": 50,  # Brake release delay
        "PC24": 100, # Forced stop decel
        "PB18": 10,  # Current filter / command smoothing
        "PE02": 50,  # Friction compensation
        "PE07": 0    # Backlash compensation
    })
    
    # 1. 共振抑制 Notch Filter 寫入
    peak = ai.get("fft_resonance_peak")
    if peak and float(peak) > 0:
        writes["PA18"] = int(round(peak))
        writes["PB12"] = int(round(peak * 1.5))
        
    # 2. 遺失運動與反向間隙補償 (Lost Motion Compensation) -> S04 漂移 & S09 減速機背隙
    if root in ["encoder_drift", "gearbox_backlash"] or "encoder_drift" in root:
        drift = ai.get("encoder_drift_pulse", 120.0)
        writes["PE07"] = int(round(drift * 0.8)) # 補償 80% 穩態間隙
        
    # 3. 摩擦力補償 (Friction Compensation) -> 軸承磨損與卡阻
    if root in ["bearing", "bearing_wear", "ball_screw_friction"] or ai.get("friction_estimate_nm", 0.0) > 0:
        friction = ai.get("friction_estimate_nm", 1.5)
        writes["PE02"] = int(round(friction * 100.0)) # 轉換為對應參數單位

    # --- 以下為 核心參數微調寫入邏輯 ---
    # 4. 位置誤差過大 / 響應不足 (following_error) -> 增加增益
    if root in ["following_error", "following_error_high"]:
        writes["PB07"] = int(round(current_params.get("PB07", 100) * 1.10))
        writes["PB08"] = int(round(current_params.get("PB08", 150) * 1.10))
        
    # 5. 增益不穩定 / 迴路振盪 (gain_instability / overshoot_high) -> 降低增益
    elif root in ["gain_instability", "overshoot_high"]:
        writes["PB07"] = int(round(current_params.get("PB07", 100) * 0.90))
        writes["PB08"] = int(round(current_params.get("PB08", 150) * 0.90))
        
    # 6. 超溫 / 過熱 (motor_over_temp / drive_over_temp / thermal) -> 降低扭矩限制
    elif root in ["motor_over_temp", "drive_over_temp", "thermal"]:
        writes["PA11"] = int(round(current_params.get("PA11", 300) * 0.90))
        writes["PA12"] = int(round(current_params.get("PA12", 300) * 0.90))
        
    # 7. 煞車失效 (brake_failure) -> 增加煞車延遲
    elif root == "brake_failure":
        writes["PC16"] = int(round(current_params.get("PC16", 50) * 1.20))
        
    # 8. 緊急停止 (emergency_stop) -> 平滑強停減速
    elif root == "emergency_stop":
        writes["PC24"] = int(round(current_params.get("PC24", 100) * 1.20))

    # --- 以下為 新增的 S07-S22 & S24 調參計算 ---
    # 9. S07: coupling_misalignment -> 降低速度增益 5%
    elif root == "coupling_misalignment":
        writes["PB08"] = int(round(current_params.get("PB08", 150) * 0.95))
    # 10. S08: belt_slack -> 降低位置增益 5%
    elif root == "belt_slack":
        writes["PB07"] = int(round(current_params.get("PB07", 100) * 0.95))
    # 11. S11: phase_loss -> 降低轉矩限制 PA11 10%
    elif root == "phase_loss":
        writes["PA11"] = int(round(current_params.get("PA11", 300) * 0.90))
    # 12. S12: bus_overvoltage -> 增加減速時間 PC24 20%
    elif root == "bus_overvoltage":
        writes["PC24"] = int(round(current_params.get("PC24", 100) * 1.20))
    # 13. S13: bus_undervoltage -> 增加加速時間 PC24 20%
    elif root == "bus_undervoltage":
        writes["PC24"] = int(round(current_params.get("PC24", 100) * 1.20))
    # 14. S14: mechanical_jam -> 降低轉矩限制 PA11 10%
    elif root == "mechanical_jam":
        writes["PA11"] = int(round(current_params.get("PA11", 300) * 0.90))
    # 15. S16: ground_noise -> 增加指令濾波 PB18 10%
    elif root == "ground_noise":
        writes["PB18"] = int(round(current_params.get("PB18", 10) * 1.10))
    # 16. S17: limit_active -> 減少煞車動作延遲 PC16 10%
    elif root == "limit_active":
        writes["PC16"] = int(round(current_params.get("PC16", 50) * 0.90))
    # 17. S18: accel_aggressive -> 增加加減速時間 PC24 20%
    elif root == "accel_aggressive":
        writes["PC24"] = int(round(current_params.get("PC24", 100) * 1.20))
    # 18. S19: dynamic_brake_fail -> 增加煞車動作延遲 PC16 20%
    elif root == "dynamic_brake_fail":
        writes["PC16"] = int(round(current_params.get("PC16", 50) * 1.20))
    # 19. S20: command_jitter -> 增加濾波 PB18 10%
    elif root == "command_jitter":
        writes["PB18"] = int(round(current_params.get("PB18", 10) * 1.10))
    # 20. S21: inertia_mismatch -> 增加自動響應 PA09 1格
    elif root == "inertia_mismatch":
        writes["PA09"] = int(round(current_params.get("PA09", 12) + 1))
        
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
