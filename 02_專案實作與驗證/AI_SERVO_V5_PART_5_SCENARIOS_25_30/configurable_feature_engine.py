#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SERVO PLATFORM - Configurable Feature Engine
Loads JSON scenario specs and dynamically computes derived features using physical/DSP algorithms.
"""

import os
import json
import numpy as np
from dsp_analytics import TimeDomainFeatureExtractor, AdvancedMechanicalDiagnostics, AdvancedElectricalDiagnostics, BodeResponseAnalyzer

class ConfigurableFeatureEngine:
    def __init__(self, json_dir, buffer_size=1000):
        self.json_dir = json_dir
        self.buffer_size = buffer_size
        self.scenarios = {}
        self.buffer = {}  # Dynamic buffers for each signal tag
        self.bode_analyzer = BodeResponseAnalyzer(sampling_rate_hz=1000)
        self.load_all_scenarios()

    def load_all_scenarios(self):
        """Loads all scenario JSON templates in the directory"""
        if not os.path.exists(self.json_dir):
            print(f"[FEATURE ENGINE] WARNING: JSON Directory {self.json_dir} does not exist.")
            return

        for filename in os.listdir(self.json_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.json_dir, filename)
                try:
                    # JSON containing comments? Read line by line and skip comment lines
                    lines = []
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            stripped = line.strip()
                            if stripped.startswith("//") or stripped.startswith("#"):
                                continue
                            lines.append(line)
                    json_str = "".join(lines)
                    
                    spec = json.loads(json_str)
                    sc_id = spec.get("scenario_id")
                    if sc_id:
                        self.scenarios[sc_id] = spec
                        print(f"[FEATURE ENGINE] Successfully loaded scenario: {sc_id} from {filename}")
                except Exception as e:
                    print(f"[FEATURE ENGINE] ERROR: Failed to load {filename}: {e}")

    def push_data(self, telemetry_point):
        """Pushes new telemetry data point to the rolling buffer"""
        for tag, val in telemetry_point.items():
            if tag not in self.buffer:
                self.buffer[tag] = []
            self.buffer[tag].append(val)
            # Maintain rolling window size
            if len(self.buffer[tag]) > self.buffer_size:
                self.buffer[tag].pop(0)

    def get_signal_series(self, tag):
        """Gets the rolling buffer series for a tag"""
        if tag in self.buffer and len(self.buffer[tag]) > 0:
            return np.array(self.buffer[tag])
        return np.zeros(10)  # Return default array to avoid failure

    def extract_features(self, scenario_id):
        """
        Dynamically extracts derived features for a scenario based on its JSON specification.
        Performs feature selection at the end.
        """
        # Find scenario config
        spec = None
        for key, value in self.scenarios.items():
            if key == scenario_id or key.replace('_', ' ').lower() == str(scenario_id).replace('_', ' ').lower():
                spec = value
                break

        if not spec:
            # Fallback to standard features if spec is not loaded
            # Returning raw tags present in buffers
            features = {tag: self.buffer[tag][-1] for tag in self.buffer if len(self.buffer[tag]) > 0}
            return features

        derived_output = {}
        feature_groups = spec.get("feature_groups", [])

        # Process each feature group
        for group in feature_groups:
            based_on_list = group.get("based_on")
            if isinstance(based_on_list, str):
                based_on_list = [based_on_list]

            derived_features = group.get("derived_features", [])

            for feat in derived_features:
                func_name = feat.get("function")
                out_name = feat.get("output")
                
                # Retrieve signal buffers for computation
                signals = [self.get_signal_series(tag) for tag in based_on_list]
                
                # Execute specific functions
                val = self._compute_feature(func_name, signals, based_on_list)
                derived_output[out_name] = val

        # Feature Selection
        selected_features = spec.get("selected_features_for_model", [])
        final_features = {}
        for feat_name in selected_features:
            if feat_name in derived_output:
                final_features[feat_name] = derived_output[feat_name]
            else:
                # If selected feature is missing, assign a default computed or raw value
                final_features[feat_name] = 0.0

        # Include basic system keys (time, run_index, transitions, etc.)
        for key in ["time", "run_index", "transitions", "ylabel", "DV"]:
            if key in self.buffer and len(self.buffer[key]) > 0:
                final_features[key] = self.buffer[key][-1]

        return final_features

    def _compute_feature(self, func_name, signals, based_on_list):
        """Computes derived feature based on function name and signals"""
        try:
            # Short-circuit if signals list is empty
            if not signals or len(signals[0]) == 0:
                return 0.0

            s1 = signals[0]
            
            # --- 1. Basic Statistical Functions ---
            if func_name == "rms":
                return float(np.sqrt(np.mean(s1 ** 2)))
            elif func_name == "peak":
                return float(np.max(np.abs(s1)))
            elif func_name == "std":
                return float(np.std(s1))
            elif func_name == "spectral_dominant_freq":
                # Requires position cmd vs actual or standard vibration
                if len(signals) >= 2:
                    res = self.bode_analyzer.analyze(signals[0], signals[1])
                    return float(res.get("resonance_peak_freq_hz", 0.0))
                else:
                    # Simple FFT peak on s1
                    n = len(s1)
                    fft_vals = np.abs(np.fft.rfft(s1))
                    freqs = np.fft.rfftfreq(n, d=0.001)
                    if len(fft_vals) > 1:
                        return float(freqs[np.argmax(fft_vals[1:]) + 1])
                    return 0.0

            # --- 2. Position Tracking Quality ---
            elif func_name == "max_absolute_error":
                if len(signals) >= 2:
                    return float(np.max(np.abs(signals[0] - signals[1])))
                return float(np.max(np.abs(s1)))
            elif func_name == "settling_time":
                # Estimate settling time: time taken for position error to drop below 5% of peak
                if len(signals) >= 2:
                    error = np.abs(signals[0] - signals[1])
                else:
                    error = np.abs(s1)
                peak_err = np.max(error)
                if peak_err < 1e-8:
                    return 0.05
                settled_indices = np.where(error > 0.05 * peak_err)[0]
                if len(settled_indices) > 0:
                    # Return time in seconds (approx 1ms per sample)
                    return float(settled_indices[-1] * 0.001)
                return 0.05

            # --- 3. Backlash and Stiffness (Mechanical) ---
            elif func_name == "reversal_error":
                # Needs demand, actual, velocity
                if len(signals) >= 3:
                    return AdvancedMechanicalDiagnostics.reversal_error(signals[0], signals[1], signals[2])
                elif len(signals) >= 2:
                    vel = np.gradient(signals[1])
                    return AdvancedMechanicalDiagnostics.reversal_error(signals[0], signals[1], vel)
                return 0.1
            elif func_name == "dead_zone_width":
                if len(signals) >= 3:
                    return AdvancedMechanicalDiagnostics.dead_zone_width(signals[0], signals[1], signals[2])
                elif len(signals) >= 2:
                    vel = np.gradient(signals[1])
                    return AdvancedMechanicalDiagnostics.dead_zone_width(signals[0], signals[1], vel)
                return 0.05
            elif func_name == "hysteresis_area":
                if len(signals) >= 2:
                    return AdvancedMechanicalDiagnostics.hysteresis_area(signals[0], signals[1])
                return 0.01
            elif func_name == "direction_dependent_following_error":
                if len(signals) >= 3:
                    return AdvancedMechanicalDiagnostics.direction_dependent_following_error(signals[0], signals[1], signals[2])
                elif len(signals) >= 2:
                    vel = np.gradient(signals[1])
                    return AdvancedMechanicalDiagnostics.direction_dependent_following_error(signals[0], signals[1], vel)
                return 0.05
            elif func_name == "force_displacement_slope":
                if len(signals) >= 3:
                    return AdvancedMechanicalDiagnostics.force_displacement_slope(signals[0], signals[1], signals[2])
                elif len(signals) >= 2:
                    return AdvancedMechanicalDiagnostics.force_displacement_slope(signals[0], signals[1], np.ones_like(signals[0])*100.0)
                return 100.0
            elif func_name == "compliance_std":
                if len(signals) >= 2:
                    return AdvancedMechanicalDiagnostics.compliance_std(signals[0], signals[1])
                return 0.001
            elif func_name == "elastic_region_width":
                if len(signals) >= 2:
                    return AdvancedMechanicalDiagnostics.elastic_region_width(signals[0], signals[1])
                return 0.5
            elif func_name == "stribeck_curve_parameter":
                if len(signals) >= 2:
                    _, _, stribeck = AdvancedMechanicalDiagnostics.stribeck_friction_parameters(signals[0], signals[1])
                    return stribeck
                return 0.3
            elif func_name == "coulomb_friction_estimate":
                if len(signals) >= 2:
                    coulomb, _, _ = AdvancedMechanicalDiagnostics.stribeck_friction_parameters(signals[0], signals[1])
                    return coulomb
                return 0.25
            elif func_name == "viscous_friction_coeff":
                if len(signals) >= 2:
                    _, viscous, _ = AdvancedMechanicalDiagnostics.stribeck_friction_parameters(signals[0], signals[1])
                    return viscous
                return 0.002

            # --- 4. Electrical and Demagnetization ---
            elif func_name == "fft_harmonic_amplitudes":
                # Three-phase currents
                if len(signals) >= 3:
                    return AdvancedElectricalDiagnostics.fft_harmonic_amplitudes(signals[0], signals[1], signals[2])
                return 0.01
            elif func_name == "sideband_energy_ratio":
                # Needs cmd vs actual to run Bode
                if len(signals) >= 2:
                    res = self.bode_analyzer.analyze(signals[0], signals[1])
                    return float(res.get("sideband_resonance_energy_ratio", 0.01))
                return 0.02
            elif func_name == "current_total_harmonic_distortion":
                return AdvancedElectricalDiagnostics.current_total_harmonic_distortion(s1)
            elif func_name == "phase_imbalance_index":
                if len(signals) >= 3:
                    return AdvancedElectricalDiagnostics.phase_imbalance_index(signals[0], signals[1], signals[2])
                return 0.02
            elif func_name == "id_iq_trajectory_area":
                if len(signals) >= 2:
                    return AdvancedElectricalDiagnostics.id_iq_trajectory_area(signals[0], signals[1])
                return 0.1
            elif func_name == "iq_to_torque_ratio":
                if len(signals) >= 2:
                    # Te = Kt * Iq -> Kt = Te / Iq
                    eps = 1e-8
                    return float(np.mean(signals[1] / (signals[0] + eps)))
                return 1.05
            elif func_name == "id_mean_shift":
                return float(np.mean(s1))
            elif func_name == "field_weakening_depth":
                # id mean shift is a proxy
                return float(abs(np.mean(s1)) * 0.1)
            elif func_name == "torque_ripple_factor":
                if len(signals) >= 2:
                    # std(Te) / RMS(Current)
                    eps = 1e-8
                    return float(np.std(signals[0]) / (np.sqrt(np.mean(signals[1]**2)) + eps))
                return 0.15
            elif func_name == "cogging_torque_freq":
                n = len(s1)
                fft_vals = np.abs(np.fft.rfft(s1))
                freqs = np.fft.rfftfreq(n, d=0.001)
                if len(fft_vals) > 1:
                    return float(freqs[np.argmax(fft_vals[1:]) + 1])
                return 50.0
            elif func_name == "torque_current_phase_delay":
                # Lag phase delay between Iq and Torque
                if len(signals) >= 2:
                    eps = 1e-8
                    cross_corr = np.correlate(signals[0] - np.mean(signals[0]), signals[1] - np.mean(signals[1]), mode='full')
                    delay = np.argmax(cross_corr) - len(signals[0]) + 1
                    return float(delay * 0.001)
                return 0.005

            # --- 5. Thermal & Wear ---
            elif func_name == "torque_degradation_vs_temp":
                # Slope of torque vs temp
                if len(signals) >= 2:
                    slope = np.polyfit(signals[0], signals[1], 1)[0]
                    return float(abs(slope))
                return 0.05
            elif func_name == "current_increase_vs_temp":
                if len(signals) >= 2:
                    slope = np.polyfit(signals[0], signals[1], 1)[0]
                    return float(abs(slope))
                return 0.1
            elif func_name == "thermal_recovery_time_constant":
                # Approximate thermal cooling rate
                diffs = np.diff(s1)
                cooling = diffs[diffs < 0]
                if len(cooling) > 0:
                    return float(abs(np.mean(s1) / (np.mean(cooling) + 1e-8)) * 0.001)
                return 120.0
            
            # --- 6. Defaults / Trends ---
            elif func_name == "trend_slope_over_cycles":
                # Linear trend slope of s1
                x = np.arange(len(s1))
                return float(np.polyfit(x, s1, 1)[0])
            elif func_name == "backlash_to_stiffness_ratio":
                if len(signals) >= 2:
                    eps = 1e-8
                    return float(np.mean(signals[0] / (signals[1] + eps)))
                return 0.005
            elif func_name == "position_error_asymmetry":
                return float(np.mean(s1) - np.median(s1))

        except Exception as e:
            # Graceful degradation on error
            return 0.0
        
        return 0.0
