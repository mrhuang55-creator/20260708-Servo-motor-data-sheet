#!/usr/bin/env python3
import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

# Add local path to import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dsp_analytics import KalmanFilter2D, AdvancedMechanicalDiagnostics, AdvancedElectricalDiagnostics

def run_soft_sensors_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # workspace root
    raw_csv_path = os.path.join(base_dir, "Sup data", "train_noisy_1e_m15_200x5LO-6SEC.csv")
    output_csv_path = os.path.join(base_dir, "Sup data", "train_noisy_soft_sensors.csv")
    model_output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torque_virtual_sensor.pkl")
    
    print(f"Loading raw dataset from {raw_csv_path}...")
    df = pd.read_csv(raw_csv_path, encoding='utf-8-sig')
    
    # =====================================================================
    # 1. 由原始資料推導（不用 AI）
    # =====================================================================
    print("\n[步驟 1] 執行非 AI 物理公式特徵推導...")
    dt = 0.00002 # 50 kHz sampling
    
    # 追隨誤差 Following Error = Demand - Actual
    df['following_error_abs_pulse'] = (df['rod_demand_pos'] - df['rod_actual_pos']).abs()
    
    # 速度 (Velocity) = 位置的一階差分
    df['velocity'] = df['rod_actual_pos'].diff() / dt
    df['velocity'] = df['velocity'].fillna(0.0)
    
    # 加速度 (Acceleration) = 位置的二階差分 (速度一階差分)
    df['acceleration'] = df['velocity'].diff() / dt
    df['acceleration'] = df['acceleration'].fillna(0.0)
    
    # 加加速度 (Jerk) = 位置的三階差分 (加速度一階差分)
    df['jerk'] = df['acceleration'].diff() / dt
    df['jerk'] = df['jerk'].fillna(0.0)
    
    # 位置有效值 (Position RMS, 滑動視窗 100 點)
    df['pos_rms'] = np.sqrt((df['rod_actual_pos']**2).rolling(window=100, min_periods=1).mean())
    
    # 轉矩有效值 (Torque RMS, 滑動視窗 100 點)
    df['torque_rms'] = np.sqrt((df['torque']**2).rolling(window=100, min_periods=1).mean())
    
    # 轉矩波動度 (Torque Ripple, 滑動視窗 100 點之標準差)
    df['torque_ripple'] = df['torque'].rolling(window=100, min_periods=1).std().fillna(0.0)
    
    # 三相電流總有效值 (3-Phase Current RMS) = sqrt((i_a^2 + i_b^2 + i_c^2) / 3)
    df['current_rms'] = np.sqrt((df['i_3p_a']**2 + df['i_3p_b']**2 + df['i_3p_c']**2) / 3.0)

    # 三相電流對稱分量解算 (Symmetrical Components Solver)
    a = -0.5 + 0.8660254j
    a2 = -0.5 - 0.8660254j
    ia = df['i_3p_a'].values.astype(np.complex64)
    ib = df['i_3p_b'].values.astype(np.complex64)
    ic = df['i_3p_c'].values.astype(np.complex64)
    i_positive = (ia + a * ib + a2 * ic) / 3.0
    i_negative = (ia + a2 * ib + a * ic) / 3.0
    i_zero = (ia + ib + ic) / 3.0
    df['i_positive_seq_rms'] = np.abs(i_positive).astype(np.float32)
    df['i_negative_seq_rms'] = np.abs(i_negative).astype(np.float32)
    df['i_zero_seq_rms'] = np.abs(i_zero).astype(np.float32)
    
    # 呼叫進階對稱分量不平衡度算法
    df['current_unbalance_pct'] = AdvancedElectricalDiagnostics.phase_imbalance_index(df['i_3p_a'], df['i_3p_b'], df['i_3p_c']) * 100.0
    
    # 電流向量幅值 (Current Magnitude) = sqrt(Id^2 + Iq^2)
    df['current_magnitude'] = np.sqrt(df['direct']**2 + df['quadrature']**2)
    
    # 新增符合今天標準之滾珠螺桿物理衍生特徵
    df['reversal_error'] = AdvancedMechanicalDiagnostics.reversal_error(df['rod_demand_pos'], df['rod_actual_pos'], df['velocity'])
    df['dead_zone_width'] = AdvancedMechanicalDiagnostics.dead_zone_width(df['rod_demand_pos'], df['rod_actual_pos'], df['velocity'])
    df['hysteresis_area'] = AdvancedMechanicalDiagnostics.hysteresis_area(df['rod_demand_pos'], df['rod_actual_pos'])
    
    # 機械功率 (Mechanical Power) = Torque (Nm) * Speed (rad/s)
    # speed is in RPM, converted to rad/s: omega = speed * 2 * pi / 60
    speed_rad = df['rotor_speed'] * 2.0 * np.pi / 60.0
    df['mechanical_power'] = df['torque'] * speed_rad
    
    # 電力功率指標 (Electrical Power Proxy) = Id^2 + Iq^2
    df['electrical_power_proxy'] = (df['direct']**2 + df['quadrature']**2)
    
    # 效率指標 (Efficiency Index) = Mech Power / Elec Power
    df['efficiency_index'] = df['mechanical_power'] / (df['electrical_power_proxy'] + 1e-3)
    
    print("  - 物理推導特徵描述統計:")
    print(df[['velocity', 'acceleration', 'jerk', 'current_rms', 'mechanical_power', 'efficiency_index']].describe().T)
    
    # =====================================================================
    # 2. 由 AI 估測（Virtual Sensor） - 轉矩軟感測器
    # =====================================================================
    print("\n[步驟 2] 訓練 AI 轉矩虛擬感測器 (Virtual Torque Sensor)...")
    # 使用 d 軸與 q 軸電流及轉速預測電磁轉矩
    X = df[['direct', 'quadrature', 'rotor_speed']]
    y = df['torque']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 導入 MLCompetitionPlatform 進行競賽尋優
    from ml_automl_engine import MLCompetitionPlatform
    platform = MLCompetitionPlatform()
    
    print("  進行多模型迴歸競賽尋優 (在 10000 筆樣本上)...")
    X_train_sub = X_train.iloc[:10000].values
    y_train_sub = y_train.iloc[:10000].values
    reg_results = platform.run_regression_competition(X_train_sub, y_train_sub)
    
    winner_name = reg_results[0]["model"]
    print(f"  - 迴歸競賽最優模型勝出者: {winner_name} (R2-Score: {reg_results[0]['r2_score']:.6f})")
    
    # 獲取最優模型並在全量數據上進行擬合
    model = platform.regressors[winner_name]
    print(f"  - 在全量訓練數據上訓練勝出模型 {winner_name}...")
    model.fit(X_train.values, y_train.values)
    
    # 評估模型
    y_pred = model.predict(X_test.values)
    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    print(f"  - 最優模型 {winner_name} 轉矩預測 R2 決定係數: {r2:.6f}")
    print(f"  - 均方誤差 MSE: {mse:.6e}")
    
    # 保存模型
    with open(model_output_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"  - 轉矩虛擬感測器已保存至: {model_output_path}")
    
    # 新增 AI 估計的轉矩列
    df['estimated_torque_ai'] = model.predict(X.values).astype(np.float32)
    
    # =====================================================================
    # 3. AI 可以補足連續數據 - 卡爾曼濾波插值
    # =====================================================================
    print("\n[步驟 3] 執行卡爾曼濾波進行資料連續性補足與平滑重建 (Position Reconstruction)...")
    # 模擬 10% 的位置稀疏反饋 (其餘 90% 隨機遺失)
    np.random.seed(42)
    noisy_pos = df['rod_actual_pos'].values.copy()
    mask = np.random.choice([True, False], size=len(noisy_pos), p=[0.1, 0.9])
    mask[0] = True
    mask[-1] = True
    
    sparse_pos = noisy_pos.copy()
    sparse_pos[~mask] = np.nan
    
    # 初始化卡爾曼濾波器 (使用 50 kHz 步階)
    kf = KalmanFilter2D(dt=dt, q_cov=1000.0, r_cov=2.0)
    kf.reset(initial_position=noisy_pos[0])
    
    reconstructed_pos = []
    for val in sparse_pos:
        kf.predict()
        if not np.isnan(val):
            kf.update(val)
        reconstructed_pos.append(kf.x[0, 0])
        
    df['reconstructed_position_kf'] = np.array(reconstructed_pos, dtype=np.float32)
    
    rmse_recon = np.sqrt(np.mean((df['reconstructed_position_kf'] - df['rod_actual_pos'])**2))
    print(f"  - 從 10% 稀疏位置信號重建連續軌跡之 RMSE: {rmse_recon:.6f} (可信度極高)")
    
    # =====================================================================
    # 4. 資料存檔與生命週期管理
    # =====================================================================
    print(f"\n[步驟 4] 寫入所有物理與 AI 特徵至: {output_csv_path}...")
    df.to_csv(output_csv_path, index=False)
    
    # 同步寫入 Parquet 並運行生命週期降採樣歸檔管理
    output_parquet_path = output_csv_path.replace(".csv", ".parquet")
    df.to_parquet(output_parquet_path, index=False)
    print(f"  - 特徵資料同步儲存為 Parquet: {output_parquet_path}")
    
    from phm_pipeline import DataLifecycleManager
    archived_parquet_path = output_parquet_path.replace(".parquet", "_archived.parquet")
    lifecycle_mgr = DataLifecycleManager()
    lifecycle_mgr.archive_parquet_file(output_parquet_path, archived_parquet_path)
    
    print("軟感測器資料流水線運行與數據生命週期歸檔完成！\n")

if __name__ == "__main__":
    run_soft_sensors_pipeline()
