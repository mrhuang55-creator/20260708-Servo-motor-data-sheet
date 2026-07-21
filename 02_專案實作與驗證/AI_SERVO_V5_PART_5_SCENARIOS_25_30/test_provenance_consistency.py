#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SERVO PLATFORM Diagnostic Consistency Guard Test
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent path to import ai_engine and tag_provenance
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import ai_engine
import tag_provenance

# Helper function to generate clean baseline row
def get_clean_row():
    return {
        "following_error_abs_pulse": 0.0,
        "motor_temp_c": 50.0,
        "drive_temp_c": 45.0,
        "vibration_rms_g": 0.1,
        "bearing_bpfo_amp": 0.0,
        "bearing_bpfi_amp": 0.0,
        "torque_error_nm": 0.0,
        "current_rms_a": 1.0,
        "network_jitter_ms": 0.1,
        "ethercat_sync_error_us": 5.0,
        "ethercat_packet_loss_pct": 0.0,
        "plc_scan_time_ms_anomaly": 0.0,
        "plc_estop_active": 0.0,
        "brake_status_bool": 0.0,
        "current_unbalance_pct": 0.0,
        "frequency_response_100hz_db": 0.0,
        "resonance_frequency_hz": 0.0,
        "digital_twin_pos_residual": 0.0,
        "digital_twin_speed_residual": 0.0,
        "fft_1x_amp": 0.0,
        "health_index": 100.0,
        "rul_sec": 9999.0,
        "encoder_error_count": 0.0,
        "encoder_drift_pulse": 0.0
    }

# Triggers list for each Scenario ID
SCENARIO_TRIGGERS = {
    1: {},
    2: {"motor_temp_c": 91.0},
    3: {"drive_temp_c": 86.0},
    4: {"encoder_drift_pulse": 101.0},
    5: {"encoder_error_count": 51.0},
    6: {"encoder_error_count": 1001.0},
    7: {"following_error_abs_pulse": 111.0},
    8: {"digital_twin_speed_residual": 181.0},
    9: {"torque_error_nm": 0.71},
    10: {"following_error_abs_pulse": 151.0},
    11: {"current_rms_a": 9.1},
    12: {"torque_error_nm": 1.01},
    13: {"plc_estop_active": 1.0, "torque_error_nm": 1.4},
    14: {"bearing_bpfo_amp": 0.71},
    15: {"torque_error_nm": 0.56},
    16: {"vibration_rms_g": 0.31, "fft_1x_amp": 0.41, "frequency_response_100hz_db": 20.0},
    17: {"vibration_rms_g": 0.36, "frequency_response_100hz_db": 16.0},
    18: {"encoder_drift_pulse": 21.0},
    19: {"encoder_drift_pulse": 36.0},
    20: {"vibration_rms_g": 0.26, "resonance_frequency_hz": 50.0},
    21: {"current_unbalance_pct": 3.1},
    22: {"current_unbalance_pct": 2.1},
    23: {"network_jitter_ms": 2.1},
    24: {"ethercat_packet_loss_pct": 2.1, "following_error_abs_pulse": 101.0},
    25: {"following_error_abs_pulse": 121.0, "frequency_response_100hz_db": 16.0},
    26: {"vibration_rms_g": 0.41, "frequency_response_100hz_db": 26.0},
    27: {"brake_status_bool": 1.0},
    28: {"plc_estop_active": 1.0},
    29: {"motor_temp_c": 91.0, "vibration_rms_g": 0.36},
    30: {"health_index": 34.0},
    31: {"vibration_rms_g": 0.23, "following_error_abs_pulse": 100.0},
    32: {"torque_error_nm": 0.46, "vibration_rms_g": 0.29, "bearing_bpfo_amp": 0.5},
    33: {"torque_error_nm": 1.3},
    34: {"motor_temp_c": 81.0, "current_rms_a": 8.1, "torque_error_nm": 0.4},
    35: {"current_unbalance_pct": 4.3},
    36: {"torque_error_nm": 1.71, "vibration_rms_g": 0.36},
    37: {"following_error_abs_pulse": 106.0, "torque_error_nm": 0.91},
    38: {"vibration_rms_g": 0.27, "following_error_abs_pulse": 80.0, "frequency_response_100hz_db": 10.0},
    39: {"encoder_drift_pulse": 51.0},
    40: {"current_rms_a": 7.1, "current_unbalance_pct": 1.9}
}

def run_consistency_checks():
    print("==========================================================")
    print(">>> 執行 一致性防呆測試：40 個情境與判定規則對照檢查")
    print("==========================================================")
    
    passed = True
    errors = []
    
    for sid in range(1, 41):
        # 1. 建立基準行資料並套用觸發特徵值
        row = get_clean_row()
        trigger_vals = SCENARIO_TRIGGERS.get(sid, {})
        for col, val in trigger_vals.items():
            row[col] = val
            
        # 2. 轉換為 DataFrame 送入 ai_engine.diagnose
        df = pd.DataFrame([row])
        res = ai_engine.diagnose(df)
        
        # 3. 獲取診斷結果與期望值進行比對
        matched_id = res["advanced_diagnostics"]["scenario_id"]
        root_cause = res["root_cause"]
        
        expected_meta = tag_provenance.DIAGNOSE_ROOT_CAUSE.get(sid, {"root": "unknown", "rule_tags": []})
        expected_root = expected_meta["root"]
        
        # 4. 斷言與結果檢查
        if matched_id != sid:
            passed = False
            err_msg = f"Scenario {sid}: 期望診斷出 ID {sid}，但實際回傳 ID {matched_id}"
            errors.append(err_msg)
            print(f"  [\033[91mFAIL\033[0m] {err_msg}")
        elif root_cause != expected_root:
            passed = False
            err_msg = f"Scenario {sid}: 期望 root 為 '{expected_root}'，但實際回傳 '{root_cause}'"
            errors.append(err_msg)
            print(f"  [\033[91mFAIL\033[0m] {err_msg}")
        else:
            print(f"  [\033[92mPASS\033[0m] Scenario {sid:02d}: {res['advanced_diagnostics']['scenario_name']} | root: {root_cause}")
            
    print("==========================================================")
    if passed:
        print("  [\033[92mSUCCESS\033[0m] 所有 40 個情境診斷規則與 tag_provenance.py 登記完全一致！")
        sys.exit(0)
    else:
        print(f"  [\033[91mFAILURE\033[0m] 發現 {len(errors)} 個不一致的邏輯缺口！")
        for err in errors:
            print(f"    * {err}")
        sys.exit(1)

if __name__ == "__main__":
    run_consistency_checks()
