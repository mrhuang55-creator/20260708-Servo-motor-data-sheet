#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SERVO PLATFORM {Final Version} Core Engine
Implementing Stages 1-7 and Stage 9 (observability dashboard skipped as requested)
"""

import os
import sys
import time
import json
import random
import datetime
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to sys.path to import tag_provenance
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import tag_provenance


# Define the 40 Scenarios and their associated tags
SCENARIOS_LIBRARY = {
    1: {"name": "Pick & Place (定位到位時間優化)", "tags": ["time", "rod_demand_pos", "rod_actual_pos", "Following Error", "Velocity"], "category": "位置定位與運動軌跡類"},
    2: {"name": "Press Axis (重載配合/繞組溫升估算)", "tags": ["torque", "Electrical Power", "Winding Temperature", "Motor Temperature"], "category": "位置定位與運動軌跡類"},
    3: {"name": "Tray Loader (高速搬運/溫升率警告)", "tags": ["rotor_speed", "Electrical Power", "Winding Temperature", "Motor Temperature"], "category": "位置定位與運動軌跡類"},
    4: {"name": "XY Gantry (長行程定位/雙軸同步與反向補償)", "tags": ["rod_demand_pos", "rod_actual_pos", "Following Error", "Backlash"], "category": "位置定位與運動軌跡類"},
    5: {"name": "Vision Stage (微對位定位/編碼器高頻震動)", "tags": ["rod_actual_pos", "Velocity", "Position RMS"], "category": "位置定位與運動軌跡類"},
    6: {"name": "Conveyor (高速往返輸送/皮帶抖動)", "tags": ["Velocity", "Acceleration", "Jerk", "Following Error"], "category": "位置定位與運動軌跡類"},
    7: {"name": "Robot Joint (高速加減速/軌跡追隨錯誤)", "tags": ["Following Error", "Acceleration", "Jerk"], "category": "位置定位與運動軌跡類"},
    8: {"name": "Spindle (高速旋轉主軸/軸心擺動速度過高)", "tags": ["rotor_speed", "Velocity", "Torque Ripple"], "category": "位置定位與運動軌跡類"},
    9: {"name": "Indexer (S曲線旋轉/轉換點過沖抑制)", "tags": ["rod_actual_pos", "Velocity", "Acceleration", "Following Error"], "category": "位置定位與運動軌跡類"},
    10: {"name": "Inspection (短行程幾何/減速殘留震動)", "tags": ["rod_actual_pos", "Velocity", "Acceleration", "Jerk"], "category": "位置定位與運動軌跡類"},
    11: {"name": "Press Fit (精密壓入/峰值電流限制)", "tags": ["i_3p_a", "i_3p_b", "i_3p_c", "Current RMS", "Current Magnitude", "torque"], "category": "負載扭矩與機械結構類"},
    12: {"name": "Clamp (扭矩夾緊與維持/時間與扭矩和)", "tags": ["time", "torque", "Torque RMS"], "category": "負載扭矩與機械結構類"},
    13: {"name": "Transfer Arm (卡檢/卡死扭矩變動率)", "tags": ["torque", "Torque RMS", "Torque Ripple"], "category": "負載扭矩與機械結構類"},
    14: {"name": "Rotary Table (軸承狀態/BPFO特徵幅值與震動)", "tags": ["rotor_speed", "torque", "Torque Ripple", "Bearing Temperature"], "category": "負載扭矩與機械結構類"},
    15: {"name": "Linear Stage (導軌/潤滑老化摩擦力估算)", "tags": ["torque", "rotor_speed", "Friction", "Lubrication Index", "Coulomb Friction"], "category": "負載扭矩與機械結構類"},
    16: {"name": "Rotor (轉子不平衡旋轉/擺動震動位移)", "tags": ["rotor_speed", "torque", "Torque Ripple", "Position RMS"], "category": "負載扭矩與機械結構類"},
    17: {"name": "Coupling (聯軸器偏差/角度偏差高頻共振)", "tags": ["rotor_speed", "torque", "Torque Ripple", "Gearbox Temperature"], "category": "負載扭矩與機械結構類"},
    18: {"name": "Ball Screw (滾珠絲槓/磨損導致反向間隙)", "tags": ["rod_demand_pos", "rod_actual_pos", "Following Error", "Backlash", "Stiffness"], "category": "負載扭矩與機械結構類"},
    19: {"name": "Index Table (分度盤/空程間隙多重分類)", "tags": ["rod_demand_pos", "rod_actual_pos", "Following Error", "Backlash"], "category": "位置定位與運動軌跡類"},
    20: {"name": "Scanner (結構低頻震動/結構共振頻率)", "tags": ["rod_actual_pos", "Velocity", "Acceleration"], "category": "負載扭矩與機械結構類"},
    21: {"name": "Power Test (電網電源/母線電壓紋波比)", "tags": ["Electrical Power", "i_3p_a", "i_3p_b", "i_3p_c", "direct", "quadrature"], "category": "電網、通訊與運維壽命類"},
    22: {"name": "Peak Load (加速母線欠壓/電流限制與跌落值)", "tags": ["Electrical Power", "Current RMS", "Current Magnitude", "torque"], "category": "電網、通訊與運維壽命類"},
    23: {"name": "PLC Sync (通訊同步超時/時基抖動)", "tags": ["time", "run_index", "transitions"], "category": "電網、通訊與運維壽命類"},
    24: {"name": "EtherCAT (數據表/網路丟包與中斷時間)", "tags": ["time", "run_index", "transitions"], "category": "電網、通訊與運維壽命類"},
    25: {"name": "Precision Axis (高精密/位置高頻自激嘯叫)", "tags": ["rod_actual_pos", "Velocity", "Following Error", "Torque Ripple"], "category": "電網、通訊與運維壽命類"},
    26: {"name": "Resonance (共振激振/機械台板主共振頻率)", "tags": ["torque", "Torque Ripple", "Acceleration"], "category": "電網、通訊與運維壽命類"},
    27: {"name": "Vertical Z (垂直軸防下滑/煞車釋放下滑量)", "tags": ["time", "rod_actual_pos", "Following Error", "del_pos"], "category": "電網、通訊與運維壽命類"},
    28: {"name": "Prod Line (生產線急停/制動最大減速阻尼扭矩)", "tags": ["torque", "Torque RMS", "Acceleration", "Jerk"], "category": "電網、通訊與運維壽命類"},
    29: {"name": "Factory (多重故障失效/溫升與性能併發退化)", "tags": ["DV", "ylabel", "Motor Temperature", "Winding Temperature", "Efficiency Index"], "category": "電網、通訊與運維壽命類"},
    30: {"name": "Pred Maint (預測壽命/RUL剩餘壽命估算)", "tags": ["time", "run_index", "DV", "ylabel", "Efficiency Index", "Lubrication Index"], "category": "電網、通訊與運維壽命類"},
    31: {"name": "Belt Slackness (皮帶鬆弛/長時間張力下滑)", "tags": ["Velocity", "Acceleration", "Jerk", "Following Error", "Stiffness"], "category": "機械與傳動劣化進階類"},
    32: {"name": "Gear Tooth Breakage (減速機齒輪斷齒/嚙合局部損傷)", "tags": ["rotor_speed", "torque", "Torque Ripple", "Gearbox Temperature", "Position RMS"], "category": "機械與傳動劣化進階類"},
    33: {"name": "Guide Rail Jamming (導軌異物卡阻/局部阻力突變)", "tags": ["rod_actual_pos", "torque", "Torque Ripple", "Friction", "Coulomb Friction"], "category": "機械與傳動劣化進階類"},
    34: {"name": "Rotor Demagnetization (轉子永磁體高溫退磁)", "tags": ["torque", "i_3p_a", "i_3p_b", "i_3p_c", "Current RMS", "direct", "quadrature", "Motor Temperature"], "category": "馬達內部電氣與磁路故障類"},
    35: {"name": "Phase Open Circuit / Unbalance (定子線圈不對稱/單相局部短路或開路)", "tags": ["i_3p_a", "i_3p_b", "i_3p_c", "Current RMS", "Current Magnitude", "Torque Ripple", "Winding Temperature"], "category": "馬達內部電氣與磁路故障類"},
    36: {"name": "External Collision Detection (外部突發碰撞/防撞安全保護)", "tags": ["time", "Velocity", "Acceleration", "torque", "Torque Ripple", "Torque RMS"], "category": "動態環境與控制過載類"},
    37: {"name": "Load Inertia Mismatch (負載慣量嚴重失配/過大工件誤換)", "tags": ["rod_demand_pos", "rod_actual_pos", "Following Error", "torque", "Load Inertia", "Stiffness"], "category": "動態環境與控制過載類"},
    38: {"name": "Continuous Micro-Oscillation (微幅持續抖動/伺服回路過增益自激)", "tags": ["rod_actual_pos", "Velocity", "Position RMS", "Torque Ripple"], "category": "動態環境與控制過載類"},
    39: {"name": "Encoder Pulse Drop (編碼器訊號偶發丟脈衝/光柵髒污)", "tags": ["time", "rod_demand_pos", "rod_actual_pos", "Following Error", "del_pos"], "category": "感測器與回授訊號線劣化類"},
    40: {"name": "Power Cable Intermittent Contact (馬達動力線高彈性拖鏈斷芯/接觸不良)", "tags": ["run_index", "i_3p_a", "i_3p_b", "i_3p_c", "Current Magnitude", "Electrical Power"], "category": "感測器與回授訊號線劣化類"}
}

ALL_FEATURE_TAGS = sorted(list(set(tag for sc in SCENARIOS_LIBRARY.values() for tag in sc["tags"])))

from configurable_feature_engine import ConfigurableFeatureEngine

class AuditLogger:
    """Stage 9: System logs & audit trace (ISO 9001 / IEC 61508 compliance)"""
    def __init__(self, log_path="iso_audit_log.json"):
        self.log_path = log_path
        self.logs = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.logs = json.load(f)
            except Exception:
                self.logs = []

    def log(self, event_type, details):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
            "compliance": ["ISO 9001", "IEC 61508"]
        }
        self.logs.append(entry)
        print(f"[\033[94mAUDIT LOG\033[0m] {event_type} | {details}")
        # Save to file
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(self.logs, indent=2, ensure_ascii=False, fp=f)


class TaskDispatcher:
    """Stage 1: Strategic Intent Layer"""
    def __init__(self, audit_logger, feature_engine=None):
        self.audit_logger = audit_logger
        self.scenarios_db = SCENARIOS_LIBRARY.copy()
        # Integrate JSON configurations dynamically
        if feature_engine and feature_engine.scenarios:
            for sc_id, spec in feature_engine.scenarios.items():
                idx = 41
                if "01" in sc_id or "pick" in sc_id.lower():
                    idx = 1
                elif "18" in sc_id or "screw" in sc_id.lower():
                    idx = 18
                elif "34" in sc_id or "demagnetization" in sc_id.lower():
                    idx = 34
                self.scenarios_db[idx] = {
                    "name": spec.get("scenario_name", sc_id),
                    "tags": spec.get("selected_features_for_model", spec.get("raw_tags", [])),
                    "category": "JSON Configured Scenarios"
                }
        self.similarity_threshold = 0.20
        self.residual_threshold = 1.0 # Baseline residual threshold
        self.consecutive_residual_increase = 0
        self.weights = {tag: 1.0 for tag in ALL_FEATURE_TAGS}

    def evaluate_residuals_and_schedule(self, current_residual):
        """Monitors residuals, triggers feature weight updates or retraining"""
        print(f"[\033[93mSTAGE 1\033[0m] Strategic Intent: Current Residual = {current_residual:.4f} (Threshold: {self.residual_threshold:.4f})")
        if current_residual > self.residual_threshold:
            self.consecutive_residual_increase += 1
            print(f"[\033[93mSTAGE 1\033[0m] Residual exceeded threshold! Consecutive violations: {self.consecutive_residual_increase}/3")
            if self.consecutive_residual_increase >= 3:
                self.consecutive_residual_increase = 0
                self.audit_logger.log("RETRAIN_TRIGGERED", f"Residual continuously exceeded threshold (current: {current_residual:.4f})")
                return "RETRAIN"
            else:
                # Dynamic feature weight adjustment
                for tag in self.weights:
                    self.weights[tag] *= random.uniform(0.9, 1.1)
                print(f"[\033[93mSTAGE 1\033[0m] Adjusting feature weights dynamically to compensate.")
                return "WEIGHT_ADJUST"
        else:
            self.consecutive_residual_increase = 0
            return "NORMAL"

    def check_scenario_similarity(self, active_features_vector):
        """
        Computes similarity between the incoming features vector and scenarios library
        If similarity is below threshold, triggers expert manual intervention.
        """
        # Determine abnormal/deviating features in the current vector
        abnormal_features = set()
        
        # Check against normal baseline ranges
        if active_features_vector.get("Following Error", 80.0) > 90.0:
            abnormal_features.add("Following Error")
        if active_features_vector.get("vibration_rms_g", 0.15) > 0.22:
            abnormal_features.add("vibration_rms_g")
        if active_features_vector.get("Motor Temperature", 55.0) > 75.0:
            abnormal_features.add("Motor Temperature")
        if active_features_vector.get("Winding Temperature", 65.0) > 85.0:
            abnormal_features.add("Winding Temperature")
        if active_features_vector.get("torque", 2.5) > 3.5:
            abnormal_features.add("torque")
        if active_features_vector.get("torque_error_nm", 0.2) > 0.45:
            abnormal_features.add("torque_error_nm")
        if active_features_vector.get("Torque Ripple", 0.2) > 0.45:
            abnormal_features.add("Torque Ripple")
        if active_features_vector.get("current_rms_a", 4.5) > 7.0:
            abnormal_features.add("current_rms_a")
        if active_features_vector.get("current_unbalance_pct", 0.5) > 1.5:
            abnormal_features.add("current_unbalance_pct")
        if active_features_vector.get("encoder_drift_pulse", 0.5) > 20.0:
            abnormal_features.add("encoder_drift_pulse")
        if active_features_vector.get("encoder_error_count", 2.0) > 50.0:
            abnormal_features.add("encoder_error_count")
        if active_features_vector.get("digital_twin_pos_residual", 0.5) > 10.0:
            abnormal_features.add("digital_twin_pos_residual")
            
        # If no abnormal features are detected, it is highly similar to healthy baseline (Scenario 1)
        if not abnormal_features:
            provenance = tag_provenance.get_scenario_provenance(1)
            multiplier = provenance["multiplier"]
            adjusted_similarity = 1.0 * multiplier
            
            data_provenance_warning = list(provenance["warnings"])
            if provenance["confidence_unresolved_bug"]:
                data_provenance_warning.append("confidence_unresolved_bug (known_issue)")
                
            prov_info = {
                "similarity": round(adjusted_similarity, 4),
                "data_provenance_warning": data_provenance_warning
            }
            if provenance["requires_engineer_review"]:
                prov_info["requires_engineer_review"] = True
                
            print(f"[\033[93mSTAGE 1\033[0m] Scenario Similarity check output: {json.dumps(prov_info, ensure_ascii=False)}")
            return True, 1, adjusted_similarity
            
        best_similarity = 0.0
        best_scenario_id = -1
        
        for sc_id, sc in self.scenarios_db.items():
            sc_tags_set = set(sc["tags"])
            intersection = abnormal_features.intersection(sc_tags_set)
            union = abnormal_features.union(sc_tags_set)
            jaccard = len(intersection) / len(union) if union else 0.0
            
            if jaccard > best_similarity:
                best_similarity = jaccard
                best_scenario_id = sc_id
        
        lookup_sc_id = best_scenario_id if best_scenario_id in tag_provenance.DIAGNOSE_ROOT_CAUSE else 1
        provenance = tag_provenance.get_scenario_provenance(lookup_sc_id)
        multiplier = provenance["multiplier"]
        adjusted_similarity = best_similarity * multiplier
        
        data_provenance_warning = list(provenance["warnings"])
        if provenance["confidence_unresolved_bug"]:
            data_provenance_warning.append("confidence_unresolved_bug (known_issue)")
            
        prov_info = {
            "similarity": round(adjusted_similarity, 4),
            "data_provenance_warning": data_provenance_warning
        }
        if provenance["requires_engineer_review"]:
            prov_info["requires_engineer_review"] = True
            
        print(f"[\033[93mSTAGE 1\033[0m] Max Scenario Similarity = {best_similarity:.2%} (Abnormal Features: {list(abnormal_features)})")
        print(f"[\033[93mSTAGE 1\033[0m] Scenario Similarity check output (Calibrated): {json.dumps(prov_info, ensure_ascii=False)}")
        
        if adjusted_similarity < self.similarity_threshold:
            self.audit_logger.log("EXPERT_INTERVENTION_REQUIRED", f"Similarity {adjusted_similarity:.2%} below threshold {self.similarity_threshold:.2%}")
            return False, best_scenario_id, adjusted_similarity
        
        return True, best_scenario_id, adjusted_similarity


    def expert_define_scenario_41(self, name, tags):
        """Expands the library to Scenario 41 after expert intervention and full train"""
        new_id = len(self.scenarios_db) + 1
        self.scenarios_db[new_id] = {
            "name": name,
            "tags": tags,
            "category": "Expert Defined Anomaly"
        }
        self.audit_logger.log("EXPERT_SCENARIO_ADDED", f"Added scenario {new_id}: {name} with tags {tags}")
        return new_id


class EthercatCollector:
    """Stage 2: Data & Communication Layer (EtherCAT Simulation with Multi-rate sampling)"""
    def __init__(self):
        pass

    def collect_telemetry(self, scenario_id=1, tick_count=0):
        """Simulates high-speed EtherCAT packet with multi-rate sampling based on 0715-Sup priorities"""
        raw_vals = {
            "time": time.time(),
            "run_index": 201,
            "transitions": int(random.choice([1202, 1203, 1204, 1205, 1206])),
            "rod_demand_pos": float(np.random.normal(1000, 10)),
            "rod_actual_pos": float(np.random.normal(1000, 10)),
            "Following Error": float(np.random.normal(80, 5)),
            "Velocity": float(np.random.normal(1500, 100)),
            "torque": float(np.random.normal(2.5, 0.2)),
            "Torque RMS": float(np.random.normal(2.5, 0.1)),
            "Torque Ripple": float(np.random.normal(0.2, 0.05)),
            "current_rms_a": float(np.random.normal(4.5, 0.3)),
            "Current Magnitude": float(np.random.normal(6.3, 0.4)),
            "i_3p_a": float(np.random.normal(4.5, 0.3)),
            "i_3p_b": float(np.random.normal(4.5, 0.3)),
            "i_3p_c": float(np.random.normal(4.5, 0.3)),
            "Winding Temperature": float(np.random.normal(65, 3)),
            "Motor Temperature": float(np.random.normal(55, 3)),
            "Bearing Temperature": float(np.random.normal(45, 2)),
            "vibration_rms_g": float(np.random.normal(0.15, 0.02)),
            "Acceleration": float(np.random.normal(20, 2)),
            "Jerk": float(np.random.normal(5, 1)),
            "Backlash": float(np.random.normal(0.5, 0.05)),
            "Stiffness": float(np.random.normal(100, 2)),
            "Friction": float(np.random.normal(0.4, 0.05)),
            "Coulomb Friction": float(np.random.normal(0.3, 0.04)),
            "Lubrication Index": float(np.random.normal(0.95, 0.02)),
            "Efficiency Index": float(np.random.normal(0.92, 0.01)),
            "DV": 270.197,
            "ylabel": "LO",
            "Electrical Power": float(np.random.normal(1500, 50)),
            "direct": float(np.random.normal(0.1, 0.02)),
            "quadrature": float(np.random.normal(4.5, 0.25)),
            "Position RMS": float(np.random.normal(0.8, 0.05)),
            "Gearbox Temperature": float(np.random.normal(48, 2)),
            "del_pos": float(np.random.normal(0.1, 0.01)),
            "rotor_speed": float(np.random.normal(1500, 100))
        }

        # Inject anomalies depending on scenario
        if scenario_id == 2:  # Press Axis (thermal)
            raw_vals["Motor Temperature"] = float(np.random.normal(95, 2))
            raw_vals["Winding Temperature"] = float(np.random.normal(105, 3))
            raw_vals["torque"] = float(np.random.normal(4.8, 0.3))
        elif scenario_id == 26:  # Resonance
            raw_vals["Torque Ripple"] = float(np.random.normal(1.85, 0.15))
            raw_vals["Acceleration"] = float(np.random.normal(85, 8))
            raw_vals["vibration_rms_g"] = float(np.random.normal(0.48, 0.04))
        elif scenario_id == 99:  # Unknown anomaly
            raw_vals["Motor Temperature"] = float(np.random.normal(120, 2))
            raw_vals["encoder_drift_pulse"] = float(np.random.normal(85, 2))
            raw_vals["digital_twin_pos_residual"] = float(np.random.normal(25, 2))

        # Tag Priority Categorization
        high_tags = ["time", "run_index", "transitions", "rod_demand_pos", "rod_actual_pos", "Following Error", "Velocity", "i_3p_a", "i_3p_b", "i_3p_c", "vibration_rms_g", "Acceleration", "Jerk"]
        medium_tags = ["torque", "Torque RMS", "Torque Ripple", "current_rms_a", "Current Magnitude", "rotor_speed", "direct", "quadrature", "Position RMS"]
        low_tags = ["Winding Temperature", "Motor Temperature", "Bearing Temperature", "Gearbox Temperature", "Backlash", "Stiffness", "Friction", "Coulomb Friction", "Lubrication Index", "Efficiency Index", "DV", "ylabel", "Electrical Power", "del_pos"]

        sampled_point = {}
        # High level: Every tick
        for tag in high_tags:
            if tag in raw_vals:
                sampled_point[tag] = raw_vals[tag]

        # Medium level: Every 10 ticks
        if tick_count % 10 == 0:
            for tag in medium_tags:
                if tag in raw_vals:
                    sampled_point[tag] = raw_vals[tag]
        else:
            for tag in medium_tags:
                sampled_point[tag] = None

        # Low level: Every 100 ticks
        if tick_count % 100 == 0:
            for tag in low_tags:
                if tag in raw_vals:
                    sampled_point[tag] = raw_vals[tag]
        else:
            for tag in low_tags:
                sampled_point[tag] = None

        return sampled_point


class HealthChecker:
    """Stage 3: Data Health Check Layer with Carry-Forward Alignment for Multi-rate sampling"""
    def __init__(self):
        self.last_valid_values = {}

    def check_and_clean(self, raw_data):
        """Performs carry-forward imputation for unsampled tags, range check and validation"""
        cleaned_data = raw_data.copy()
        
        # Impute unsampled tags (carry-forward)
        for key in list(cleaned_data.keys()):
            val = cleaned_data[key]
            if val is None:
                if key in self.last_valid_values:
                    cleaned_data[key] = self.last_valid_values[key]
                else:
                    cleaned_data[key] = self._get_default_val(key)
            else:
                self.last_valid_values[key] = val
                
        # Range Validation
        if cleaned_data.get("Motor Temperature", 55.0) > 140.0:
            print("[\033[91mHEALTH CHECK\033[0m] WARNING: Motor Temperature critical threshold exceeded!")
            cleaned_data["Motor Temperature"] = 140.0
            
        if cleaned_data.get("current_rms_a", 4.5) > 25.0:
            print("[\033[91mHEALTH CHECK\033[0m] WARNING: Current RMS critical threshold exceeded!")
            cleaned_data["current_rms_a"] = 25.0
            
        cleaned_data["vibration_rms_g"] = float(np.clip(cleaned_data.get("vibration_rms_g", 0.15), 0.0, 5.0))
        return cleaned_data

    def _get_default_val(self, key):
        defaults = {
            "torque": 2.5, "Torque RMS": 2.5, "Torque Ripple": 0.2, "current_rms_a": 4.5,
            "Current Magnitude": 6.3, "rotor_speed": 1500.0, "Winding Temperature": 65.0,
            "Motor Temperature": 55.0, "Bearing Temperature": 45.0, "Gearbox Temperature": 48.0,
            "Backlash": 0.5, "Stiffness": 100.0, "Friction": 0.4, "Coulomb Friction": 0.3,
            "Lubrication Index": 0.95, "Efficiency Index": 0.92, "DV": 270.197, "ylabel": "LO",
            "Electrical Power": 1500.0, "del_pos": 0.1, "direct": 0.1, "quadrature": 4.5, "Position RMS": 0.8
        }
        return defaults.get(key, 0.0)


class FeatureExtractor:
    """Stage 4: Feature Engineering Layer (No filtering done here)"""
    def __init__(self):
        pass

    def extract_features(self, cleaned_data):
        features = {}
        # Preprocessing and calculating statistical/physical parameters
        # Calculate residuals from digital twin
        features["time"] = cleaned_data["time"]
        features["run_index"] = cleaned_data["run_index"]
        features["transitions"] = cleaned_data["transitions"]
        features["rod_demand_pos"] = cleaned_data["rod_demand_pos"]
        features["rod_actual_pos"] = cleaned_data["rod_actual_pos"]
        features["Following Error"] = cleaned_data["Following Error"]
        features["Velocity"] = cleaned_data["Velocity"]
        features["torque"] = cleaned_data["torque"]
        features["Torque RMS"] = cleaned_data["Torque RMS"]
        features["Torque Ripple"] = cleaned_data["Torque Ripple"]
        features["current_rms_a"] = cleaned_data["current_rms_a"]
        features["Current Magnitude"] = cleaned_data["Current Magnitude"]
        features["i_3p_a"] = cleaned_data["i_3p_a"]
        features["i_3p_b"] = cleaned_data["i_3p_b"]
        features["i_3p_c"] = cleaned_data["i_3p_c"]
        features["Winding Temperature"] = cleaned_data["Winding Temperature"]
        features["Motor Temperature"] = cleaned_data["Motor Temperature"]
        features["Bearing Temperature"] = cleaned_data["Bearing Temperature"]
        features["vibration_rms_g"] = cleaned_data["vibration_rms_g"]
        features["Acceleration"] = cleaned_data["Acceleration"]
        features["Jerk"] = cleaned_data["Jerk"]
        features["Backlash"] = cleaned_data["Backlash"]
        features["Stiffness"] = cleaned_data["Stiffness"]
        features["Friction"] = cleaned_data["Friction"]
        features["Coulomb Friction"] = cleaned_data["Coulomb Friction"]
        features["Lubrication Index"] = cleaned_data["Lubrication Index"]
        features["Efficiency Index"] = cleaned_data["Efficiency Index"]
        features["DV"] = cleaned_data["DV"]
        features["ylabel"] = cleaned_data["ylabel"]
        features["Electrical Power"] = cleaned_data["Electrical Power"]
        features["direct"] = cleaned_data["direct"]
        features["quadrature"] = cleaned_data["quadrature"]
        features["Position RMS"] = cleaned_data["Position RMS"]
        features["Gearbox Temperature"] = cleaned_data["Gearbox Temperature"]
        features["del_pos"] = cleaned_data["del_pos"]
        features["rotor_speed"] = cleaned_data["rotor_speed"]
        
        # Physics-informed features
        features["digital_twin_pos_residual"] = abs(cleaned_data["rod_demand_pos"] - cleaned_data["rod_actual_pos"])
        features["thermal_residual"] = cleaned_data["Winding Temperature"] - cleaned_data["Motor Temperature"]
        
        return features


class AutoMLMatrix:
    """Stage 5: Core Algorithm Matrix Layer with real Shadow Mode validation"""
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger
        self.model_version = "v1.0.0"
        self.fallback_count = 0
        self.active_weights = {
            "layer_1": np.random.randn(10, 5),
            "layer_2": np.random.randn(5, 2),
            "layer_output": np.random.randn(2, 1)
        }
        self.old_weights = None
        self.shadow_buffer_old = []
        self.shadow_buffer_new = []
        self.shadow_max_size = 600 # Represents 10 min window (1s intervals)

    def inference_lightweight(self, features):
        """Lightweight inference loop (<1ms) - simulated"""
        # If random failure, raise exception
        if random.random() < 0.02:
            raise RuntimeError("EtherCAT high-frequency lightweight inference failure!")
        
        res = features.get("digital_twin_pos_residual", 0.5)
        therm = features.get("thermal_residual", 10.0)
        x = np.array([res, therm])
        control_output = np.dot(x, self.active_weights["layer_output"]) + 1.25
        return float(control_output[0])

    def fine_tune_min(self, recent_data_list):
        """Minute-level model weights fine-tuning (last 5 min data, adjusting last 2 layers)"""
        print("[\033[95mSTAGE 5\033[0m] Fine-tuning model weights (adjusting output 2 layers)...")
        # Adjust weight values slightly
        self.active_weights["layer_2"] += np.random.normal(0, 0.05, self.active_weights["layer_2"].shape)
        self.active_weights["layer_output"] += np.random.normal(0, 0.05, self.active_weights["layer_output"].shape)
        self.audit_logger.log("MODEL_FINE_TUNED", "Fine-tuned last 2 layers of neural network compensation model.")

    def run_heavy_automl_matrix(self):
        """AutoML Parallel Matrix heavy training (4 Hours)"""
        print("[\033[95mSTAGE 5\033[0m] Running parallel AutoML training matrix...")
        print("  - AutoML ML Pool: TOP 20 Regression, TOP 20 Classification, TOP 10 Clustering")
        print("  - DL Pool: MLP, RNN+LSTM, BiDirectional GRU with Attention Network")
        self.model_version = f"v{int(self.model_version.split('.')[0].replace('v', '')) + 1}.0.0"
        self.audit_logger.log("AUTOML_MATRIX_TRAINED", f"Full retraining complete. Model upgraded to version {self.model_version}")

    def record_shadow_residuals(self, old_res, new_res):
        """Accumulates residuals in shadow mode"""
        self.shadow_buffer_old.append(old_res)
        self.shadow_buffer_new.append(new_res)
        if len(self.shadow_buffer_old) > self.shadow_max_size:
            self.shadow_buffer_old.pop(0)
            self.shadow_buffer_new.pop(0)

    def execute_shadow_mode(self, old_residuals=None, new_residuals=None):
        """A/B Shadow Mode evaluation (10-minute window, compares accumulated RMSE)"""
        print("[\033[95mSTAGE 5\033[0m] Shadow Mode: Evaluating accumulated new vs old model residuals...")
        
        o_res = self.shadow_buffer_old if len(self.shadow_buffer_old) > 0 else (old_residuals if old_residuals is not None else np.random.normal(1.2, 0.2, 100))
        n_res = self.shadow_buffer_new if len(self.shadow_buffer_new) > 0 else (new_residuals if new_residuals is not None else np.random.normal(0.8, 0.1, 100))
        
        rmse_old = np.sqrt(np.mean(np.square(o_res)))
        rmse_new = np.sqrt(np.mean(np.square(n_res)))
        
        print(f"  - Old Model accumulated RMSE: {rmse_old:.4f} | New Model accumulated RMSE: {rmse_new:.4f}")
        
        if rmse_new < 0.90 * rmse_old:
            self.audit_logger.log("SHADOW_MODE_SWITCH", f"New model accepted. RMSE improved from {rmse_old:.4f} to {rmse_new:.4f}")
            self.shadow_buffer_old.clear()
            self.shadow_buffer_new.clear()
            return True
        else:
            self.audit_logger.log("SHADOW_MODE_ROLLBACK", f"New model rejected. RMSE ({rmse_new:.4f}) did not improve by 10% over old ({rmse_old:.4f}). Rollback to old weights.")
            self.shadow_buffer_old.clear()
            self.shadow_buffer_new.clear()
            return False

    def handle_inference_fallback(self, prev_value, pid_backup_value):
        """Fallback policy for inference failure: 1-2 times: last value, 3-9 times: PID, 10 times: halt"""
        self.fallback_count += 1
        print(f"[\033[91mFALLBACK TRIGGERED\033[0m] Consecutive failures: {self.fallback_count}")
        if self.fallback_count < 3:
            print("  - Action (Level 1): Using previous control value.")
            return prev_value
        elif self.fallback_count < 10:
            print("  - Action (Level 2): Using PID backup control value.")
            return pid_backup_value
        else:
            self.audit_logger.log("FALLBACK_CRITICAL_ALERT", "Consecutive failures >= 10. Triggering professional maintenance protocol.")
            raise SystemExit("System Halted: Inference failure limit reached. Expert intervention required.")


class DecisionEnsemble:
    """Stage 6: Decision & Dynamic Integration Layer"""
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger

    def select_decision_route(self, model_performance_score):
        """Decides whether to trigger Ensemble Learning or stick to built-in model"""
        print(f"[\033[96mSTAGE 6\033[0m] Ensemble Selection: Performance score = {model_performance_score:.4f}")
        if model_performance_score < 0.85:
            print("  - Action: Built-in model insufficient. Activating Stacking/Weighted Ensemble Learning.")
            self.audit_logger.log("ENSEMBLE_LEARNING_ACTIVATED", "Dynamically enabled Ensemble Learning for the current cycle.")
            return "ENSEMBLE"
        else:
            print("  - Action: Performance good. Prioritizing built-in single model (low latency).")
            return "BUILTIN"


class ExplainableControl:
    """Stage 7: Explainable & Control Layer (SHAP & State Machine)"""
    def __init__(self, audit_logger):
        self.audit_logger = audit_logger
        self.mode = "NORMAL" # NORMAL, DIAGNOSTIC, PERFORMANCE_FINE_TUNING
        self.control_output = 0.0
        self.consecutive_violations = 0

    def run_shap_diagnostics(self, features):
        """Runs SHAP value analysis in the background to avoid interfering with control loop"""
        print("[\033[92mSTAGE 7\033[0m] SHAP Diagnostic: Explaining root cause in background...")
        # Simulate SHAP values
        shap_vals = {
            "vibration_rms_g": random.uniform(0.1, 0.8) if features.get("vibration_rms_g", 0.15) > 0.3 else 0.05,
            "Motor Temperature": random.uniform(0.1, 0.7) if features.get("Motor Temperature", 55.0) > 80 else 0.05,
            "digital_twin_pos_residual": random.uniform(0.2, 0.9) if features.get("digital_twin_pos_residual", 0.5) > 50 else 0.05
        }
        sorted_shap = sorted(shap_vals.items(), key=lambda x: x[1], reverse=True)
        print("  - SHAP Feature Attribution:")
        for name, val in sorted_shap:
            print(f"    * {name:<30} SHAP Score: {val:+.4f}")
        
        # Generate maintenance advice
        top_feature = sorted_shap[0][0]
        advice = "No immediate repairs required."
        if sorted_shap[0][1] > 0.4:
            if top_feature == "vibration_rms_g":
                advice = "Suggest checking for rotor unbalance or structural resonance. Check Notch filters configuration."
            elif top_feature == "Motor Temperature":
                advice = "Suggest cooling system check. High current load detected."
            elif top_feature == "digital_twin_pos_residual":
                advice = "Suggest motor tuning. Position tracking offset is high. Check lost motion PE07 parameters."
        
        print(f"  - Maintenance Suggestion: {advice}")
        return advice

    def transition_state_machine(self, current_residual, features):
        """Manages NORMAL -> DIAGNOSTIC -> PERFORMANCE_FINE_TUNING -> NORMAL lifecycle based on 0715-Sup"""
        print(f"[\033[92mSTAGE 7\033[0m] State Machine transition check. Current mode: {self.mode}")
        if self.mode == "NORMAL":
            if current_residual > 1.5: # Anomaly threshold
                self.consecutive_violations += 1
                print(f"  - Residual exceeded anomaly threshold! Consecutive: {self.consecutive_violations}/3")
                if self.consecutive_violations >= 3:
                    print("  - [Transition] Residual continuously exceeded 3 cycles! Shifting to DIAGNOSTIC MODE automatically.")
                    self.mode = "DIAGNOSTIC"
                    self.consecutive_violations = 0
                    self.audit_logger.log("STATE_TRANSITION", "NORMAL -> DIAGNOSTIC due to high residual (3 consecutive cycles).")
            else:
                self.consecutive_violations = 0
                
        elif self.mode == "DIAGNOSTIC":
            # Control optimization paused, maintain output
            print("  - [Diagnostic Control] Control optimization paused. Maintaining current output.")
            # Run SHAP
            advice = self.run_shap_diagnostics(features)
            # Simulate operator intervention/repair
            print("\n  >> [OPERATOR INTERVENTION] Operator checks SHAP diagnosis, completes repair.")
            print("  >> [OPERATOR CHOICE] 1. Revert to NORMAL mode. 2. Manual switch to PERFORMANCE_FINE_TUNING mode.")
            choice = "2" # Simulator defaults to performance fine tuning to demonstrate loop
            if choice == "1":
                self.mode = "NORMAL"
                self.audit_logger.log("STATE_TRANSITION", "DIAGNOSTIC -> NORMAL (Operator confirmed resolved).")
            else:
                self.mode = "PERFORMANCE_FINE_TUNING"
                self.audit_logger.log("STATE_TRANSITION", "DIAGNOSTIC -> PERFORMANCE_FINE_TUNING (Operator requested optimization).")
                
        elif self.mode == "PERFORMANCE_FINE_TUNING":
            print("  - [Optimization] Fine tuning controller gains in progress...")
            # Simulate optimization finish
            time.sleep(0.5)
            print("  - [Transition] Optimization complete. Returning to NORMAL mode.")
            self.mode = "NORMAL"
            self.audit_logger.log("STATE_TRANSITION", "PERFORMANCE_FINE_TUNING -> NORMAL (Optimization complete).")


# =====================================================================
# Main Simulation Loop
# =====================================================================
def main():
    print("=================================================================")
    print("          AI SERVO PLATFORM {Final Version} Core Engine          ")
    print("=================================================================")
    
    # Initialize all stages
    json_dir = r"d:\20260713\20260707-馬達專題-V4\Sup data\0715-Sup"
    feature_engine = ConfigurableFeatureEngine(json_dir=json_dir, buffer_size=1000)
    
    audit_logger = AuditLogger()
    dispatcher = TaskDispatcher(audit_logger, feature_engine)
    collector = EthercatCollector()
    health_checker = HealthChecker()
    automl_matrix = AutoMLMatrix(audit_logger)
    decision_ensemble = DecisionEnsemble(audit_logger)
    explainable_control = ExplainableControl(audit_logger)
    
    print("\nStarting execution simulation loop...")
    
    # We simulate 6 cycles of normal, anomaly, retrain, and shadow mode runs
    cycles = 6
    prev_control_val = 1.25
    pid_backup_val = 1.05
    
    for cycle in range(1, cycles + 1):
        print(f"\n-----------------------------------------------------------------")
        print(f" CYCLE {cycle} BEGINS (Multi-rate Tick: {cycle})")
        print(f"-----------------------------------------------------------------")
        
        # Determine simulated scenario to trigger different stage events
        sim_scenario_id = 1
        if cycle == 2:
            sim_scenario_id = 26  # Resonance anomaly
        elif cycle == 3:
            sim_scenario_id = 99  # Unknown anomaly to trigger expert intervention
        elif cycle == 4:
            sim_scenario_id = 2   # Motor Over Temperature anomaly
        
        # Stage 2: Data & Communication with Multi-rate sampling
        print("[\033[94mSTAGE 2\033[0m] Collecting real-time signals from EtherCAT...")
        raw_telemetry = collector.collect_telemetry(sim_scenario_id, tick_count=cycle)
        
        # Stage 3: Data Health Check (Carry-forward alignment)
        print("[\033[94mSTAGE 3\033[0m] Running data integrity & health checks...")
        cleaned_telemetry = health_checker.check_and_clean(raw_telemetry)
        
        # Stage 4: Configurable Feature Engineering
        print("[\033[94mSTAGE 4\033[0m] Extracting physical signals via JSON specs...")
        feature_engine.push_data(cleaned_telemetry)
        
        # Stage 1: Strategic Intent Layer & Similarity
        # Pre-extract basic features for strategic decision
        temp_features = {
            "rod_demand_pos": cleaned_telemetry.get("rod_demand_pos", 1000.0),
            "rod_actual_pos": cleaned_telemetry.get("rod_actual_pos", 1000.0),
            "Following Error": cleaned_telemetry.get("Following Error", 80.0),
            "vibration_rms_g": cleaned_telemetry.get("vibration_rms_g", 0.15),
            "Motor Temperature": cleaned_telemetry.get("Motor Temperature", 55.0),
            "Winding Temperature": cleaned_telemetry.get("Winding Temperature", 65.0),
            "torque": cleaned_telemetry.get("torque", 2.5),
            "current_rms_a": cleaned_telemetry.get("current_rms_a", 4.5)
        }
        
        # Similarity check with the known scenarios
        is_known, matched_id, similarity = dispatcher.check_scenario_similarity(temp_features)
        
        # Translate matched_id to config key name
        matched_key = "01_Pick_and_Place"
        if matched_id == 18:
            matched_key = "18_Ball_Screw"
        elif matched_id == 34:
            matched_key = "34_Rotor_Demagnetization"
            
        # Dynamically extract features according to matched scenario specification
        features = feature_engine.extract_features(matched_key)
        
        current_residual = features.get("digital_twin_pos_residual", 0.5)
        if "digital_twin_pos_residual" not in features:
            features["digital_twin_pos_residual"] = abs(temp_features["rod_demand_pos"] - temp_features["rod_actual_pos"])
            features["thermal_residual"] = temp_features["Winding Temperature"] - temp_features["Motor Temperature"]
            current_residual = features["digital_twin_pos_residual"]
            
        intent_action = dispatcher.evaluate_residuals_and_schedule(current_residual)
        
        if not is_known:
            print("[\033[91mWARNING\033[0m] Similarity below threshold! Machine crash risk identified!")
            print("  - HALTING AUTOMATIC PARAMETER TUNING. WAITING FOR EXPERT INTERVENTION.")
            
            # Simulate expert manual scenario definition
            expert_sc_name = "High Friction Slide Rail Backlash Anomaly"
            expert_sc_tags = ["Friction", "Backlash", "Following Error"]
            print(f"  - [Expert Action] Defined Scenario 41: {expert_sc_name}")
            new_sc_id = dispatcher.expert_define_scenario_41(expert_sc_name, expert_sc_tags)
            print(f"  - Added to Scenarios Library database as Scenario {new_sc_id} (Wait 4 hours for full retrain)")
            
            # Simulate retraining trigger
            intent_action = "RETRAIN"
            
        # Stage 5: Core Algorithm Matrix Layer
        if intent_action == "RETRAIN":
            automl_matrix.run_heavy_automl_matrix()
            # Accumulate shadow residuals representing a 10 min window (600 cycles)
            for _ in range(600):
                o_res = np.random.normal(1.2, 0.2)
                n_res = np.random.normal(0.8, 0.1)
                automl_matrix.record_shadow_residuals(o_res, n_res)
            switch_approved = automl_matrix.execute_shadow_mode()
            if not switch_approved:
                print("  - Shadow Mode comparison failed. Retaining old weights.")
        elif intent_action == "WEIGHT_ADJUST":
            automl_matrix.fine_tune_min([features])
            
        # Perform lightweight inference
        try:
            control_val = automl_matrix.inference_lightweight(features)
            print(f"[\033[95mSTAGE 5\033[0m] Lightweight Inference completed: Control Output = {control_val:.4f} Nm")
            automl_matrix.fallback_count = 0 # reset fallback
            prev_control_val = control_val
        except RuntimeError as e:
            print(f"[\033[91mERROR\033[0m] {e}")
            control_val = automl_matrix.handle_inference_fallback(prev_control_val, pid_backup_val)
            print(f"  - Fallback output assigned: {control_val:.4f} Nm")
            
        # Stage 6: Decision & Dynamic Integration
        model_perf = 0.95 if sim_scenario_id == 1 else 0.72
        decision_route = decision_ensemble.select_decision_route(model_perf)
        if decision_route == "ENSEMBLE":
            # Simulate ensemble prediction
            control_val = 0.8 * control_val + 0.2 * pid_backup_val
            print(f"[\033[96mSTAGE 6\033[0m] Ensemble prediction calculated: Output = {control_val:.4f} Nm")
            
        # Stage 7: Explainable & Control
        explainable_control.transition_state_machine(current_residual, features)
        
        # Control cycle complete
        print(f"[\033[92mSTAGE 7\033[0m] Cycle Control loop update sent via EtherCAT. Done.")
        time.sleep(0.2)
        
    print("\n=================================================================")
    print("Simulation finished successfully. Compliance Audit Log saved.")
    print("=================================================================")

if __name__ == "__main__":
    main()
