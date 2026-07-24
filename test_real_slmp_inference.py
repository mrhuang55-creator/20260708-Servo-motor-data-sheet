#!/usr/bin/env python3
"""
SLMP 連接馬達 AI PHM 推論整合測試腳本
對接 SLMPServerMock / SLMPClient 與 AIServo_模型交付包
"""
import os
import sys
import time

# 動態新增搜尋路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DELIVERY_PKG_DIR = os.path.join(BASE_DIR, "Sup data", "AIServo_模型交付包")
PART5_DIR = os.path.join(BASE_DIR, "02_專案實作與驗證", "AI_SERVO_V5_PART_5_SCENARIOS_25_30")

if DELIVERY_PKG_DIR not in sys.path:
    sys.path.insert(0, DELIVERY_PKG_DIR)
if PART5_DIR not in sys.path:
    sys.path.insert(0, PART5_DIR)

from slmp_client import SLMPClient, SLMPServerMock
from src.models.servo_predict import predict_servo, load_servo_models

def run_connected_motor_test():
    print("======================================================================")
    print(">>> 執行已連線馬達 (SLMP MC 3E) 的 AI 診斷與推論測試")
    print("======================================================================")
    
    # 1. 啟動 SLMP 伺服馬達模擬器 (模擬實體馬達連線)
    server = SLMPServerMock(host="127.0.0.1", port=5009)
    server.registers[1000] = 0     # 狀態暫存器: 無 E-Stop
    server.registers[1001] = 450   # 溫度 45.0 °C
    server.registers[1002] = 250   # 電流 2.50 A
    server.registers[1003] = 120   # 振動 0.12 g
    server.registers[1004] = 15    # 1X FFT 振幅 1.5
    server.registers[1005] = 5     # 共振振幅 0.5
    server.registers[1006] = 8     # 數位雙生殘差 0.008
    server.start()
    print("  [伺服馬達通訊] 已連接至馬達站點 (127.0.0.1:5009)...")

    # 2. 建立 SLMP 客戶端連線
    client = SLMPClient(host="127.0.0.1", port=5009)
    client.connect()

    try:
        # 3. 批次讀取馬達暫存器 (D1000 - D1006)
        regs = client.read_d_registers(start_addr=1000, points=7)
        print(f"  [暫存器讀取] D1000-D1006 數據: {regs}")

        # 4. 硬體斷言檢查 (Rule 2.3 E-Stop 覆蓋)
        plc_estop_active = bool(regs[0] & 0x01)
        if plc_estop_active:
            print("  [硬體斷言觸發] 檢測到 PLC E-Stop！強制歸類為 Scenario 28 (Emergency Stop)")
            return

        # 5. 取得模型期望的 21 個特徵欄位並自動填充馬達數據
        bundle = load_servo_models()
        feature_columns = bundle.feature_columns

        # 基礎特徵 map
        base_features = {
            "rotor_speed_mean": 10.0,
            "rotor_speed_std": 50.0,
            "rotor_speed_rms": 52.0,
            "torque_mean": 0.0,
            "torque_std": 5.0,
            "torque_rms": 5.0,
            "del_pos_mean": 10.0,
            "del_pos_std": 5.0,
            "del_pos_rms": 12.0,
            "i_3p_a_rms": regs[2] / 100.0,
            "i_3p_b_rms": regs[2] / 100.0,
            "i_3p_c_rms": regs[2] / 100.0,
            "direct_rms": 0.25,
            "direct_std": 0.25,
            "quadrature_rms": 5.0,
            "quadrature_std": 5.0,
            "rod_demand_pos_mean": 300.0,
            "rod_actual_pos_mean": 300.0 - (regs[6] / 1000.0),
            "position_error_mean": regs[6] / 1000.0,
            "position_error_max": (regs[6] / 1000.0) * 1.5,
            "position_error_std": (regs[6] / 1000.0) * 0.5
        }

        # 6. 調用交付包模型進行診斷
        diagnosis = predict_servo(base_features, bundle=bundle)
        print(f"\n  [AI 診斷與推論結果]:")
        print(f"    - predicted_health_state: {diagnosis.get('predicted_health_state')}")
        print(f"    - health_state_zh:        {diagnosis.get('health_state_zh')}")
        print(f"    - model_confidence:       {diagnosis.get('model_confidence')}")
        print(f"    - degradation_score:      {diagnosis.get('degradation_score')}")
        print(f"    - health_score:           {diagnosis.get('health_score')}")
        print(f"    - risk_level:             {diagnosis.get('risk_level')}")
        print(f"    - top_features:           {diagnosis.get('top_features')[:2]}")
        print(f"    - maintenance_advice:     {diagnosis.get('maintenance_advice')}")
        
    finally:
        client.close()
        server.stop()
        print("\n  [測試完成] 已斷開連線並關閉模擬器。")

if __name__ == "__main__":
    run_connected_motor_test()
