#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SERVO PLATFORM Data Provenance Classification & Calibration Module
"""

# Base TAG_PROVENANCE dictionary containing all 53 tags (including custom ones)
TAG_PROVENANCE = {
    # 1. raw (1.0)
    "time": "raw",
    "DV": "raw",
    "rod_demand_pos": "raw",
    "rod_actual_pos": "raw",
    "torque": "raw",
    "rotor_speed": "raw",
    "i_3p_a": "raw",
    "i_3p_b": "raw",
    "i_3p_c": "raw",
    "direct": "raw",
    "quadrature": "raw",
    "run_index": "raw",
    "transitions": "raw",
    "del_pos": "raw",
    "ylabel": "raw",
    
    # 2. derived (0.95)
    "following_error_abs_pulse": "derived",
    "Velocity": "derived",
    "Acceleration": "derived",
    "Jerk": "derived",
    "Position RMS": "derived",
    "Torque RMS": "derived",
    "torque_error_nm": "derived",
    "current_rms_a": "derived",
    "Current Magnitude": "derived",
    "Electrical Power": "derived",
    "Mechanical Power": "derived",
    "Efficiency Index": "derived",
    "health_index": "derived", # Proposed custom tag (derived)
    
    # 3. virtual_sensor (0.7)
    "motor_temp_c": "virtual_sensor",
    "Winding Temperature": "virtual_sensor",
    "Bearing Temperature": "virtual_sensor",
    "Gearbox Temperature": "virtual_sensor",
    "Friction": "virtual_sensor",
    "Lubrication Index": "virtual_sensor",
    "Backlash": "virtual_sensor",
    "Stiffness": "virtual_sensor",
    "Load Inertia": "virtual_sensor",
    "Coulomb Friction": "virtual_sensor",
    "drive_temp_c": "virtual_sensor",
    
    # 4. unavailable (0.4)
    "vibration_rms_g": "unavailable",
    "bearing_bpfo_amp": "unavailable",
    "bearing_bpfi_amp": "unavailable",
    "digital_twin_pos_residual": "unavailable",
    "encoder_drift_pulse": "unavailable",
    "encoder_error_count": "unavailable",
    "digital_twin_speed_residual": "unavailable", # Proposed custom tag
    "fft_1x_amp": "unavailable",                 # Proposed custom tag
    
    # 5. fabricated_not_in_dataset (0.3)
    "network_jitter_ms": "fabricated_not_in_dataset",
    "ethercat_sync_error_us": "fabricated_not_in_dataset",
    "ethercat_packet_loss_pct": "fabricated_not_in_dataset",
    "plc_scan_time_ms_anomaly": "fabricated_not_in_dataset",
    "plc_estop_active": "fabricated_not_in_dataset",
    "brake_status_bool": "fabricated_not_in_dataset",
    "current_unbalance_pct": "fabricated_not_in_dataset",
    "frequency_response_100hz_db": "fabricated_not_in_dataset",
    "resonance_frequency_hz": "fabricated_not_in_dataset"
}

# Multiplier table for confidence scaling
PROVENANCE_CONFIDENCE_MULTIPLIER = {
    "raw": 1.0,
    "derived": 0.95,
    "virtual_sensor": 0.7,
    "unavailable": 0.4,
    "fabricated_not_in_dataset": 0.3
}

# Tag name aliases (mapping CamelCase / spaces to canonical snake_case keys)
TAG_NAME_ALIAS = {
    "Following Error": "following_error_abs_pulse",
    "following_error": "following_error_abs_pulse",
    "Motor Temperature": "motor_temp_c",
    "thermal_motor": "motor_temp_c",
    "thermal_drive": "drive_temp_c",
    "Torque Ripple": "torque_error_nm",
    "torque_ripple": "torque_error_nm",
    "Current RMS": "current_rms_a",
    "current_load": "current_rms_a",
    "Vibration": "vibration_rms_g",
    "vibration": "vibration_rms_g",
    "bearing": "bearing_bpfo_amp",
    "digital_twin_error": "digital_twin_pos_residual",
    "encoder_drift": "encoder_drift_pulse",
    "encoder_noise": "encoder_error_count",
    "encoder_signal_loss": "encoder_error_count"
}

# Scenario ID to checked diagnostic tags mapping (Diagnostic Logic Tags)
DIAGNOSE_ROOT_CAUSE = {
    1: {"root": "normal", "rule_tags": []},
    2: {"root": "motor_over_temp", "rule_tags": ["motor_temp_c"]},
    3: {"root": "drive_over_temp", "rule_tags": ["drive_temp_c"]},
    4: {"root": "encoder_drift", "rule_tags": ["encoder_drift_pulse"]},
    5: {"root": "encoder_noise", "rule_tags": ["encoder_error_count"]},
    6: {"root": "encoder_signal_loss", "rule_tags": ["encoder_error_count"]},
    7: {"root": "position_deviation_too_large", "rule_tags": ["following_error_abs_pulse"]},
    8: {"root": "over_speed", "rule_tags": ["digital_twin_speed_residual"]},
    9: {"root": "acceleration_overshoot", "rule_tags": ["torque_error_nm"]},
    10: {"root": "deceleration_failure", "rule_tags": ["following_error_abs_pulse"]},
    11: {"root": "over_current", "rule_tags": ["current_rms_a"]},
    12: {"root": "torque_saturation", "rule_tags": ["torque_error_nm"]},
    13: {"root": "jam", "rule_tags": ["plc_estop_active", "torque_error_nm"]},
    14: {"root": "bearing_wear", "rule_tags": ["bearing_bpfo_amp"]},
    15: {"root": "lubrication_degradation", "rule_tags": ["torque_error_nm"]},
    16: {"root": "rotor_unbalance", "rule_tags": ["vibration_rms_g", "fft_1x_amp"]},
    17: {"root": "coupling_misalignment", "rule_tags": ["vibration_rms_g", "frequency_response_100hz_db"]},
    18: {"root": "lead_screw_wear", "rule_tags": ["encoder_drift_pulse"]},
    19: {"root": "gear_backlash", "rule_tags": ["encoder_drift_pulse"]},
    20: {"root": "structural_vibration", "rule_tags": ["vibration_rms_g", "resonance_frequency_hz"]},
    21: {"root": "power_grid_fluctuation", "rule_tags": ["current_unbalance_pct"]},
    22: {"root": "under_voltage_sag", "rule_tags": ["current_unbalance_pct"]},
    23: {"root": "communication_timeout", "rule_tags": ["network_jitter_ms"]},
    24: {"root": "network_packet_loss", "rule_tags": ["ethercat_packet_loss_pct", "following_error_abs_pulse"]},
    25: {"root": "gain_instability", "rule_tags": ["following_error_abs_pulse", "frequency_response_100hz_db"]},
    26: {"root": "resonance", "rule_tags": ["vibration_rms_g", "frequency_response_100hz_db"]},
    27: {"root": "brake_failure", "rule_tags": ["brake_status_bool"]},
    28: {"root": "emergency_stop", "rule_tags": ["plc_estop_active"]},
    29: {"root": "combined_fault", "rule_tags": ["motor_temp_c", "vibration_rms_g"]},
    30: {"root": "progressive_failure", "rule_tags": ["health_index"]},
    31: {"root": "belt_slackness", "rule_tags": ["vibration_rms_g", "following_error_abs_pulse"]},
    32: {"root": "gear_tooth_breakage", "rule_tags": ["torque_error_nm", "vibration_rms_g", "bearing_bpfo_amp"]},
    33: {"root": "guide_rail_jamming", "rule_tags": ["torque_error_nm", "plc_estop_active"]},
    34: {"root": "rotor_demagnetization", "rule_tags": ["motor_temp_c", "current_rms_a", "torque_error_nm"]},
    35: {"root": "phase_open_unbalance", "rule_tags": ["current_unbalance_pct"]},
    36: {"root": "external_collision", "rule_tags": ["torque_error_nm", "vibration_rms_g"]},
    37: {"root": "load_inertia_mismatch", "rule_tags": ["following_error_abs_pulse", "torque_error_nm"]},
    38: {"root": "continuous_micro_oscillation", "rule_tags": ["vibration_rms_g", "following_error_abs_pulse", "frequency_response_100hz_db"]},
    39: {"root": "encoder_pulse_drop", "rule_tags": ["encoder_drift_pulse"]},
    40: {"root": "power_cable_contact_degradation", "rule_tags": ["current_rms_a", "current_unbalance_pct"]}
}

# Root cause names mapped to scores keys (supports list mapping to resolve multi-field keys)
ROOT_TO_SCORE_MAP = {
    "normal": [],
    "motor_over_temp": ["thermal_motor"],
    "drive_over_temp": ["thermal_drive"],
    "encoder_drift": ["encoder_drift"],
    "encoder_noise": ["encoder_noise"],
    "encoder_signal_loss": ["encoder_signal_loss"],
    "position_deviation_too_large": ["following_error"],
    "over_speed": ["digital_twin_error"],
    "acceleration_overshoot": ["torque_ripple"],
    "deceleration_failure": ["following_error"],
    "over_current": ["current_load"],
    "torque_saturation": ["torque_ripple"],
    "jam": ["torque_ripple"],
    "bearing_wear": ["bearing"],
    "lubrication_degradation": ["torque_ripple"],
    "rotor_unbalance": ["vibration"],
    "coupling_misalignment": ["vibration"],
    "lead_screw_wear": ["encoder_drift"],
    "gear_backlash": ["encoder_drift"],
    "structural_vibration": ["vibration"],
    "power_grid_fluctuation": ["network"],
    "under_voltage_sag": ["network"],
    "communication_timeout": ["network"],
    "network_packet_loss": ["network"],
    "gain_instability": ["following_error"],
    "resonance": ["vibration"],
    "brake_failure": ["following_error"],
    "emergency_stop": ["network"],
    "combined_fault": ["thermal_motor", "vibration"],
    "progressive_failure": ["following_error"],
    "belt_slackness": ["following_error"],
    "gear_tooth_breakage": ["torque_ripple"],
    "guide_rail_jamming": ["torque_ripple"],
    "rotor_demagnetization": ["torque_ripple"],
    "phase_open_unbalance": ["current_load"],
    "external_collision": ["torque_ripple"],
    "load_inertia_mismatch": ["following_error"],
    "continuous_micro_oscillation": ["vibration"],
    "encoder_pulse_drop": ["encoder_drift"],
    "power_cable_contact_degradation": ["current_load"]
}

# Scenario IDs of the 6 unmapped scenarios with known unresolved confidence lookup bugs
UNRESOLVED_BUG_SCENARIOS = {21, 22, 27, 28, 30, 35}

def get_canonical_name(tag):
    """Resolves CamelCase / space tag names to canonical snake_case names."""
    return TAG_NAME_ALIAS.get(tag, tag)

def get_tag_layer(tag):
    """Gets the provenance layer for a tag."""
    canonical = get_canonical_name(tag)
    return TAG_PROVENANCE.get(canonical, "UNKNOWN")

def get_scenario_provenance(scenario_id):
    """
    Computes provenance information for a given scenario:
    - Minimum confidence scaling multiplier
    - Warning list of virtual_sensor, unavailable, or fabricated_not_in_dataset tags
    - Requires engineer review flag (True if all rule tags are fabricated)
    - Confidence unresolved bug flag (True for Scenario 21, 22, 27, 28, 30, 35)
    """
    diag = DIAGNOSE_ROOT_CAUSE.get(scenario_id, {"root": "unknown", "rule_tags": []})
    root = diag["root"]
    tags = diag["rule_tags"]
    
    warnings = []
    min_layer = "raw"
    min_mult = 1.0
    
    for t in tags:
        canonical = get_canonical_name(t)
        layer = TAG_PROVENANCE.get(canonical, "UNKNOWN")
        mult = PROVENANCE_CONFIDENCE_MULTIPLIER.get(layer, 0.0)
        
        # Non-raw layers are added to data provenance warnings
        if layer != "raw":
            warnings.append(f"{t} ({layer})")
            
        if mult < min_mult:
            min_mult = mult
            min_layer = layer
            
    # Determine if all tags checked by the rule are fabricated
    all_fabricated = False
    if tags:
        all_fabricated = all(
            get_tag_layer(t) == "fabricated_not_in_dataset"
            for t in tags
        )
        
    is_unresolved_bug = scenario_id in UNRESOLVED_BUG_SCENARIOS
    
    return {
        "scenario_id": scenario_id,
        "root_cause": root,
        "lowest_layer": min_layer,
        "multiplier": min_mult,
        "warnings": warnings,
        "requires_engineer_review": all_fabricated,
        "confidence_unresolved_bug": is_unresolved_bug
    }
