#!/usr/bin/env python3
"""
單元測試與驗證腳本: test_server_v1_api.py
使用 Python asyncio 直接測試 FastAPI 端點邏輯，包含全 41 個工況的驗證
"""
import asyncio
import unittest

import server

class TestServerV1APIAsync(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_l1_realtime(self):
        res = self.loop.run_until_complete(server.get_l1_realtime("S26: 機械共振"))
        self.assertEqual(res["level"], "L1")
        self.assertIn("predictions", res)
        self.assertIn("DV_mean", res["predictions"])
        self.assertEqual(res["scenario_id"], "26_Resonance")
        print(" [PASS] /api/v1/l1/realtime (S26 Resonance)")

    def test_02_l1_latency(self):
        res = self.loop.run_until_complete(server.get_l1_latency("01_Pick_and_Place", 60))
        self.assertIn("mean_ms", res)
        self.assertIn("p99_ms", res)
        print(" [PASS] /api/v1/l1/latency")

    def test_03_l1_model(self):
        res = self.loop.run_until_complete(server.get_l1_model("01_Pick_and_Place"))
        self.assertEqual(res["model"]["algorithm"], "LightGBM")
        print(" [PASS] /api/v1/l1/model")

    def test_04_l2_latest(self):
        res = self.loop.run_until_complete(server.get_l2_latest("01_Pick_and_Place"))
        self.assertIn("finetune", res)
        print(" [PASS] /api/v1/l2/latest")

    def test_05_l2_trend(self):
        res = self.loop.run_until_complete(server.get_l2_trend("01_Pick_and_Place", 1))
        self.assertIn("finetune_history", res)
        print(" [PASS] /api/v1/l2/trend")

    def test_06_l3_latest(self):
        res = self.loop.run_until_complete(server.get_l3_latest("01_Pick_and_Place"))
        self.assertIn("champion", res)
        self.assertEqual(res["champion"]["name"], "LightGBM_HighAcc")
        print(" [PASS] /api/v1/l3/latest")

    def test_07_l3_shadow(self):
        res = self.loop.run_until_complete(server.get_l3_shadow("01_Pick_and_Place"))
        self.assertEqual(res["decision"], "DEPLOY")
        print(" [PASS] /api/v1/l3/shadow")

    def test_08_shap_diagnosis(self):
        res = self.loop.run_until_complete(server.get_shap_diagnosis("S26: 機械共振"))
        self.assertIn("shap_values", res)
        self.assertIn("waterfall", res["shap_values"])
        self.assertEqual(res["scenario"], "26_Resonance")
        print(" [PASS] /api/v1/shap/diagnosis (S26 Resonance)")

    def test_09_shap_summary(self):
        res = self.loop.run_until_complete(server.get_shap_summary("01_Pick_and_Place"))
        self.assertIn("beeswarm", res)
        print(" [PASS] /api/v1/shap/summary")

    def test_10_fallback_events_and_stats(self):
        res_events = self.loop.run_until_complete(server.get_fallback_events(1, 20, None, None))
        self.assertIn("events", res_events)
        res_stats = self.loop.run_until_complete(server.get_fallback_stats(None, 24))
        self.assertIn("by_reason", res_stats)
        print(" [PASS] /api/v1/fallback/events & /stats")

    def test_11_scenarios_summary_full_41(self):
        res = self.loop.run_until_complete(server.get_scenarios_summary())
        scenarios = res["scenarios"]
        self.assertEqual(len(scenarios), 41)
        self.assertIn("01_Pick_and_Place", scenarios)
        self.assertIn("26_Resonance", scenarios)
        self.assertIn("41_Unknown_Profile", scenarios)
        print(" [PASS] /api/v1/scenarios (Full 41 Scenarios Verified)")

    def test_12_control_console(self):
        res_status = self.loop.run_until_complete(server.get_control_status())
        self.assertIn("system_state", res_status)
        req = server.ControlCommandRequest(command="CYCLE_START", operator="Admin_01")
        res_cmd = self.loop.run_until_complete(server.send_control_command(req))
        self.assertEqual(res_cmd["system_state"], "RUNNING")
        print(" [PASS] /api/v1/control/status & /command")

    def test_13_residual_status(self):
        res = self.loop.run_until_complete(server.get_residual_status("01_Pick_and_Place"))
        self.assertIn("threshold_3sigma", res["residual"])
        print(" [PASS] /api/v1/residual/status")

    def test_14_scenario_library_full_41(self):
        res = self.loop.run_until_complete(server.get_scenario_library())
        self.assertEqual(res["total_scenarios"], 41)
        self.assertEqual(len(res["scenarios"]), 41)
        print(" [PASS] /api/v1/scenario-library (Full 41 Scenarios Verified)")

    def test_15_ensemble_status(self):
        res = self.loop.run_until_complete(server.get_ensemble_status("01_Pick_and_Place"))
        self.assertEqual(res["ensemble_mode"], "single")
        print(" [PASS] /api/v1/ensemble/status")

    def test_16_control_mode(self):
        res = self.loop.run_until_complete(server.get_control_mode("01_Pick_and_Place"))
        self.assertIn("current_mode", res)
        print(" [PASS] /api/v1/control-mode")

    def test_17_apply_parameters_validation(self):
        # 1. 驗證無效數值 99999 被 Pydantic 攔截
        with self.assertRaises(Exception):
            server.ApplyParametersCompatRequest(scenario_id=1, parameters={"PA01": 99999})
        # 2. 測試 S28 急停互鎖 HTTP 400 攔截
        with self.assertRaises(server.HTTPException) as cm:
            self.loop.run_until_complete(server.apply_parameters_compat(server.ApplyParametersCompatRequest(scenario_id=28, parameters={"PA01": 1000})))
        self.assertEqual(cm.exception.status_code, 400)
        print(" [PASS] /api/v1/apply_parameters (Pydantic 防呆 & STO 安全互鎖驗證成功)")

    def test_18_motor_recalibration(self):
        req = server.MotorRecalibrationRequest(motor_sn="MR-J5-NEW-999", inertia_ratio=3.0)
        res = self.loop.run_until_complete(server.recalibrate_motor_parameters(req))
        self.assertEqual(res["status"], "success")
        self.assertIn("recalibrated_parameters", res)
        self.assertIn("PA01_Position_Gain", res["recalibrated_parameters"])
        print(" [PASS] /api/v1/motor/recalibrate (Motor Replacement Auto-Recalibration Verified)")

if __name__ == "__main__":
    unittest.main()
