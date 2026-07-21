#!/usr/bin/env python3
import argparse, json
from pathlib import Path

SCENARIO_DETAILS = {
    1: ("normal", "Healthy Baseline", ["PA08", "PB08"], "No adjustment needed. System is operating normally.", []),
    2: ("motor_over_temp", "Motor Over Temperature", ["PA13", "PA11", "PA12"], "Reduce motor peak acceleration/deceleration rate and duty cycle.", ["motor_temp_c", "current_rms_a"]),
    3: ("drive_over_temp", "Drive Over Temperature", ["PA13", "PC03"], "Reduce motor peak current and increase deceleration time constant.", ["drive_temp_c", "current_rms_a"]),
    4: ("encoder_drift", "Encoder Drift", ["PE01", "PE02"], "Compensate for mechanical offset and adjust backlash/friction values.", ["digital_twin_pos_residual", "encoder_drift_pulse"]),
    5: ("encoder_noise", "Encoder Noise", ["PB12", "PB26"], "Enable command filter and smoothing to filter out high-frequency noise.", ["following_error_abs_pulse", "encoder_error_count"]),
    6: ("encoder_signal_loss", "Encoder Signal Loss", ["PD05", "PC73"], "Trigger immediate emergency deceleration stop and engage brakes.", ["encoder_error_count", "health_index"]),
    7: ("position_deviation_too_large", "Position Deviation Too Large", ["PB01", "PB03", "PB05"], "Increase model loop gain and position loop gain slowly.", ["following_error_abs_pulse", "digital_twin_pos_residual"]),
    8: ("over_speed", "Over Speed", ["PA10", "PB09"], "Set strict speed limiters and inspect spindle centrifugal load.", ["digital_twin_speed_residual"]),
    9: ("acceleration_overshoot", "Acceleration Overshoot", ["PB10", "PB02"], "Adjust command filter and S-curve smoothing parameter.", ["torque_error_nm", "following_error_abs_pulse"]),
    10: ("deceleration_failure", "Deceleration Failure", ["PB45", "PB46"], "Enable advanced vibration suppression control II for residual vibration.", ["following_error_abs_pulse"]),
    11: ("over_current", "Over Current", ["PB07", "PB12"], "Configure torque/current command filter and lower peak limits.", ["current_rms_a"]),
    12: ("torque_saturation", "Torque Saturation", ["PA13", "PC03"], "Raise continuous limit if safe or reduce process load requirement.", ["torque_error_nm"]),
    13: ("jam", "Jam", ["PA13", "PC73"], "Trigger emergency deceleration stop and lock motor immediately.", ["torque_error_nm", "plc_estop_active"]),
    14: ("bearing_wear", "Bearing Wear", ["PB09", "PA10"], "Limit maximum speed and schedule bearing maintenance soon.", ["bearing_bpfo_amp", "bearing_bpfi_amp"]),
    15: ("lubrication_degradation", "Lubrication Degradation", ["PE02"], "Increase friction compensation coefficient for guide rail.", ["torque_error_nm", "current_rms_a"]),
    16: ("rotor_unbalance", "Rotor Unbalance", ["PB13"], "Enable adaptive vibration filter to suppress eccentricity vibration.", ["vibration_rms_g", "fft_1x_amp"]),
    17: ("coupling_misalignment", "Coupling Misalignment", ["PB18", "PB12"], "Tune command notch filter and check mechanical coupling alignment.", ["vibration_rms_g"]),
    18: ("lead_screw_wear", "Lead Screw Wear", ["PE01", "PE02"], "Compensate backlashes and adjust friction compensation.", ["encoder_drift_pulse"]),
    19: ("gear_backlash", "Gear Backlash", ["PE01"], "Adjust lost motion / gear deadband backlash compensation amount.", ["encoder_drift_pulse"]),
    20: ("structural_vibration", "Structural Low Frequency Vibration", ["PB45", "PB46"], "Configure advanced vibration suppression II for structure mode.", ["vibration_rms_g", "resonance_frequency_hz"]),
    21: ("power_grid_fluctuation", "Power Grid Fluctuation", ["PB12", "PC01"], "Tune torque command low-pass filter and monitor bus voltage.", ["current_unbalance_pct", "torque_error_nm"]),
    22: ("under_voltage_sag", "Under-voltage Sag", ["PA11", "PA12"], "Restrict peak current and increase deceleration time constant.", ["current_unbalance_pct"]),
    23: ("communication_timeout", "Communication Timeout", ["PB12"], "Adjust command smoothing and verify TSN synchronization.", ["network_jitter_ms", "plc_scan_time_ms_anomaly"]),
    24: ("network_packet_loss", "Network Packet Loss", ["PB12"], "Verify network cables/shielding and enable command smoothing filter.", ["ethercat_packet_loss_pct"]),
    25: ("gain_instability", "Servo Gain Instability", ["PB08", "PB09"], "Reduce position/speed loop gains or enable robust filter.", ["following_error_abs_pulse", "frequency_response_100hz_db"]),
    26: ("resonance", "Mechanical Resonance", ["PB13", "PB15"], "Configure notch filters around resonance peak.", ["vibration_rms_g", "frequency_response_100hz_db"]),
    27: ("vertical_axis_slip", "Vertical Z Axis Slip", ["PC16"], "Adjust electromagnetic brake delay and vertical axis holding limit.", ["digital_twin_pos_residual", "torque_error_nm"]),
    28: ("emergency_stop", "Emergency Stop", ["PA13"], "Execute forced stop deceleration and engage mechanical brake.", ["plc_estop_active", "following_error_abs_pulse"]),
    29: ("combined_fault", "Combined Fault", ["PA10", "PA13"], "Reduce maximum speed and limit torque command under combined stress.", ["ethercat_packet_loss_pct", "motor_temp_c"]),
    30: ("progressive_degradation", "Progressive Degradation", ["PE02"], "Schedule machine maintenance; limit maximum speed to 50%.", ["health_index", "rul_sec"]),
    31: ("belt_slackness", "Belt Slackness", ["PB01", "PB03", "PE02"], "Adjust position loop gains and friction compensation to counter belt slackness.", ["following_error_abs_pulse", "vibration_rms_g"]),
    32: ("gear_tooth_breakage", "Gear Tooth Breakage", ["PA10", "PB09"], "Limit maximum spindle speed and inspect gear wear.", ["torque_error_nm", "vibration_rms_g"]),
    33: ("guide_rail_jamming", "Guide Rail Jamming", ["PA13", "PE02"], "Increase friction compensation and enforce peak torque limiter.", ["torque_error_nm", "vibration_rms_g"]),
    34: ("rotor_demagnetization", "Rotor Demagnetization", ["PA11", "PA12"], "Configure strict torque limits and current bounds to prevent thermal run.", ["current_rms_a", "motor_temp_c"]),
    35: ("phase_open_unbalance", "Phase Open Circuit / Unbalance", ["PB07", "PB12"], "Tune command low-pass filter and check winding health.", ["current_unbalance_pct", "torque_error_nm"]),
    36: ("external_collision", "External Collision", ["PA13", "PC73"], "Trigger collision alarm, stop motor immediately to prevent physical damage.", ["torque_error_nm"]),
    37: ("load_inertia_mismatch", "Load Inertia Mismatch", ["PB01", "PB03", "PB05"], "Tune loop gains and configure inertia ratio settings.", ["following_error_abs_pulse"]),
    38: ("continuous_micro_oscillation", "Continuous Micro-Oscillation", ["PB08", "PB09"], "Lower speed and position loop gains to prevent self-excited oscillation.", ["following_error_abs_pulse"]),
    39: ("encoder_pulse_drop", "Encoder Pulse Drop", ["PB12", "PB26"], "Enable encoder noise filters and verify command pulse cable shield.", ["following_error_abs_pulse"]),
    40: ("power_cable_contact_degradation", "Power Cable Contact Degradation", ["PA13", "PC73"], "Trigger warning and schedule motor power cable replacement.", ["current_rms_a"])
}

SCENARIO_WRITES = {
    1: {"PA08": 45, "PB08": 120},
    2: {"PA13": 200, "PA11": 400, "PA12": 200},
    3: {"PA13": 500, "PC03": 300},
    4: {"PE01": 15, "PE02": 20},
    5: {"PB12": 0, "PB26": 400},
    6: {"PD05": 0, "PC73": 10},
    7: {"PB01": 0, "PB03": 5, "PB05": 150},
    8: {"PA10": 3000, "PB09": 100},
    9: {"PB10": 50, "PB02": 1},
    10: {"PB45": 150, "PB46": 20},
    11: {"PB07": 300, "PB12": 1},
    12: {"PA13": 800, "PC03": 100},
    13: {"PA13": 500, "PC73": 10},
    14: {"PB09": 120, "PA10": 2500},
    15: {"PE02": 35},
    16: {"PB13": 1},
    17: {"PB18": 450, "PB12": 0},
    18: {"PE01": 24, "PE02": 30},
    19: {"PE01": 40},
    20: {"PB45": 450, "PB46": 30},
    21: {"PB12": 2, "PC01": 10},
    22: {"PA11": 400, "PA12": 200},
    23: {"PB12": 1},
    24: {"PB12": 2},
    25: {"PB08": 90, "PB09": 80},
    26: {"PB13": 1, "PB15": 420},
    27: {"PC16": 50},
    28: {"PA13": 800},
    29: {"PA10": 1000, "PA13": 500},
    30: {"PE02": 45},
    31: {"PB01": 50, "PB03": 15, "PE02": 25},
    32: {"PA10": 2000, "PB09": 80},
    33: {"PA13": 600, "PE02": 50},
    34: {"PA11": 300, "PA12": 150},
    35: {"PB07": 250, "PB12": 2},
    36: {"PA13": 100, "PC73": 1},
    37: {"PB01": 20, "PB03": 5, "PB05": 120},
    38: {"PB08": 70, "PB09": 60},
    39: {"PB12": 1, "PB26": 200},
    40: {"PA13": 300, "PC73": 10}
}

def optimize(ai):
    # 獲取 AI 診斷結果中的情境 ID
    adv = ai.get("advanced_diagnostics", {})
    scenario_id = adv.get("scenario_id", 1)
    
    # 容錯處理：若無 scenario_id 則使用 root_cause 映射
    if scenario_id == 1 and ai.get("root_cause") != "normal":
        root = ai.get("root_cause", "normal")
        # 尋找匹配的 scenario_id
        for sid, details in SCENARIO_DETAILS.items():
            if details[0] == root:
                scenario_id = sid
                break

    cause, desc, groups, action, kpi = SCENARIO_DETAILS.get(scenario_id, SCENARIO_DETAILS[1])
    writes = SCENARIO_WRITES.get(scenario_id, {}).copy()
    
    # 自動補正共振峰
    if scenario_id == 26:
        peak = ai.get("fft_resonance_peak")
        if peak and float(peak) > 0:
            writes["PB15"] = int(round(peak))
            
    import binascii, hashlib
    payload_str = json.dumps(writes, sort_keys=True)
    crc32_val = binascii.crc32(payload_str.encode('utf-8')) & 0xffffffff
    sha256_val = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
    
    return {
        "ai_root_cause": cause,
        "confidence": ai.get("confidence", 0),
        "mr_j5_parameter_group": groups,
        "recommended_action": action,
        "trial_plan": ["Read parameters", "Set trial parameters", "Low-speed trial", "Production-speed trial", "Collect after data", "Compare KPI", "Save parameters"],
        "mr_j5_parameter_writes": writes,
        "target_kpi": kpi,
        "save_condition": "Save when KPI improvement >= 10% and no new alarm/trip is detected.",
        "security": {
            "crc32": f"0x{crc32_val:08X}",
            "sha256": sha256_val
        }
    }

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ai_result", required=True)
    p.add_argument("--out", default="optimizer_recommendation.json")
    a = p.parse_args()
    rec = optimize(json.loads(Path(a.ai_result).read_text(encoding="utf-8")))
    Path(a.out).write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(rec, indent=2, ensure_ascii=False))
