#!/usr/bin/env python3
"""
一鍵全量整合測試執行器 (Unified Project Test Suite Runner)
自動化依序跑通 7 大核心測試腳本並產出綜合報告
"""
import subprocess
import sys
import time

TEST_SCRIPTS = [
    ("Web 前端 BFF 10 大視窗與 E2E 流程", "test_frontend_routes.py"),
    ("FastAPI 19 大 REST API 與 41 工況", "test_server_v1_api.py"),
    ("異步診斷邏輯與事件佇列", "02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/test_async_diagnose.py"),
    ("DSP Bode 波德圖共振/卡爾曼/ARIMA 預測", "02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/test_dsp_analytics.py"),
    ("ML 模型競賽平台與 GA/Optuna 演算法優化", "02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/test_ml_automl.py"),
    ("深度學習 (NumPyMLP / Bi-GRU) 殘差診斷", "02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/test_deep_learning.py"),
    ("三菱 MR-J5/SLMP MC 3E 協議閉環寫入與 Rollback", "02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/test_slmp_closed_loop.py")
]

def run_all():
    print("=" * 70)
    print("  三菱 MR-J5 伺服馬達 AI 智慧健康診斷與預測維護系統")
    print("  全專案 7 大核心測試腳本與 E2E 自動化綜合測試")
    print("=" * 70)

    python_exe = sys.executable
    passed_count = 0

    for idx, (name, script) in enumerate(TEST_SCRIPTS, 1):
        print(f"\n[{idx}/7] 正在執行: {name} ({script})...")
        t0 = time.time()
        res = subprocess.run([python_exe, script], capture_output=True, text=True)
        dt = round(time.time() - t0, 3)

        if res.returncode == 0:
            passed_count += 1
            print(f"  --> [PASS] 執行成功 (耗時 {dt}s)")
        else:
            print(f"  --> [FAIL] 測試失敗 (Exit code {res.returncode})")
            print("  [錯誤細節]:", res.stderr or res.stdout[:500])

    print("\n" + "=" * 70)
    print(f"  全量測試總結: {passed_count}/{len(TEST_SCRIPTS)} 項測試通過 (成功率: {passed_count/len(TEST_SCRIPTS)*100:.1f}%)")
    print("=" * 70)
    return passed_count == len(TEST_SCRIPTS)

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
