#!/usr/bin/env python3
import os
import sys
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add local path to import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dsp_analytics import TimeDomainFeatureExtractor
def compute_rolling_features(df, window=100):
    """
    計算滾動時域高階特徵 (Kurtosis, Crest Factor, Margin Factor)
    """
    print("  計算滾動時域無量綱特徵...")
    
    # 1. 向量化高性能計算
    torque_sq = df['torque'] ** 2
    torque_rms = np.sqrt(torque_sq.rolling(window=window, min_periods=1).mean())
    torque_rms = np.clip(torque_rms, 1e-15, None)
    torque_peak = df['torque'].abs().rolling(window=window, min_periods=1).max()
    
    df['torque_crest_factor'] = (torque_peak / torque_rms).astype(np.float32)
    torque_kurt = df['torque'].rolling(window=window, min_periods=1).kurt().fillna(0.0) + 3.0
    df['torque_kurtosis'] = torque_kurt.astype(np.float32)
    torque_sqrt_mean = np.sqrt(df['torque'].abs()).rolling(window=window, min_periods=1).mean() ** 2
    torque_sqrt_mean = np.clip(torque_sqrt_mean, 1e-15, None)
    df['torque_margin_factor'] = (torque_peak / torque_sqrt_mean).astype(np.float32)

    # 2. 一致性斷言驗證 (Consistency Check with TimeDomainFeatureExtractor)
    if len(df) >= 200:
        sample_signal = df['torque'].iloc[100:200].values
        expected_crest = TimeDomainFeatureExtractor.crest_factor(sample_signal)
        # 對比向量化計算的第 200 點的值 (即 window_size=100 時的 index 199)
        actual_crest = df['torque_crest_factor'].iloc[199]
        # 由於 floating point 精度可能有些微差別，在 1e-2 內即為通過
        assert abs(expected_crest - actual_crest) < 1e-2, f"Crest factor mismatch: expected {expected_crest}, got {actual_crest}"
        print("  - [DSP 算法一致性校準] Crest Factor 向量化與 TimeDomainFeatureExtractor 靜態算法一致性驗證成功！")
        
    return df

def augment_dataset():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # workspace root
    raw_csv_path = os.path.join(base_dir, "Sup data", "train_noisy_1e_m15_200x5LO-6SEC.csv")
    output_parquet_path = os.path.join(base_dir, "Sup data", "augmented_train_data.parquet")
    
    print(f"載入原始資料集: {raw_csv_path}...")
    df_raw = pd.read_csv(raw_csv_path, encoding='utf-8-sig')
    
    # 清理行號
    df_raw = df_raw.copy()
    
    # 1. 基礎特徵計算 (在原始資料上計算)
    print("處理原始資料特徵工程...")
    df_orig = compute_rolling_features(df_raw.copy())
    
    # 2. 增強複製 A：動態雜訊注入 (Noise Injection)
    print("\n生成增強資料 A (動態雜訊注入)...")
    df_noise = df_raw.copy()
    df_noise['run_index'] = 2011  # 標記增強版本 1
    
    # 針對實體訊號注入小幅隨機高斯雜訊 (約訊號標準差的 1.5%)
    rng = np.random.default_rng(42)
    for col in ['torque', 'rotor_speed', 'i_3p_a', 'i_3p_b', 'i_3p_c']:
        col_std = df_noise[col].std()
        noise = rng.normal(0, col_std * 0.015, len(df_noise))
        df_noise[col] = df_noise[col] + noise
        
    df_noise = compute_rolling_features(df_noise)
    
    # 3. 增強複製 B：物理振幅微調縮放 (Amplitude Scaling)
    print("\n生成增強資料 B (物理振幅微調)...")
    df_scale = df_raw.copy()
    df_scale['run_index'] = 2012  # 標記增強版本 2
    
    # 對轉矩與速度乘以一個隨機物理常數因子 (0.96 - 1.04)
    scale_factor_torque = 1.02
    scale_factor_speed = 0.98
    df_scale['torque'] = df_scale['torque'] * scale_factor_torque
    df_scale['rotor_speed'] = df_scale['rotor_speed'] * scale_factor_speed
    df_scale['i_3p_a'] = df_scale['i_3p_a'] * scale_factor_torque
    df_scale['i_3p_b'] = df_scale['i_3p_b'] * scale_factor_torque
    df_scale['i_3p_c'] = df_scale['i_3p_c'] * scale_factor_torque
    
    df_scale = compute_rolling_features(df_scale)
    
    # 4. 合併所有資料 (原資料 + 增強 A + 增強 B)
    print("\n合併所有增強後之資料...")
    df_combined = pd.concat([df_orig, df_noise, df_scale], ignore_index=True)
    print(f"合併後資料總維度: {df_combined.shape}")
    
    # 5. Parquet Schema 定義與型別精確壓縮 (Schema Tuning)
    print("\n實施精確 Schema 壓縮並寫入 Parquet...")
    
    # 定義目標欄位列表與對應的 PyArrow 類型
    bool_cols = {"plc_estop_active", "brake_status_bool", "plc_scan_time_ms_anomaly"}
    
    schema_fields = []
    for col in df_combined.columns:
        if col in bool_cols:
            schema_fields.append((col, pa.bool_()))
        elif col in ['run_index', 'transitions']:
            schema_fields.append((col, pa.int32()))
        elif col == 'ylabel':
            schema_fields.append((col, pa.string()))
        else:
            schema_fields.append((col, pa.float32()))
            
    schema = pa.schema(schema_fields)
    
    # 確保 DataFrame 類型與 Schema 相容
    for col in df_combined.columns:
        if col in bool_cols:
            df_combined[col] = df_combined[col].astype(bool)
        elif col in ['run_index', 'transitions']:
            df_combined[col] = df_combined[col].astype(np.int32)
        elif col == 'ylabel':
            df_combined[col] = df_combined[col].astype(str)
        else:
            df_combined[col] = df_combined[col].astype(np.float32)
            
    # 寫入 Parquet
    table = pa.Table.from_pandas(df_combined, schema=schema)
    pq.write_table(table, output_parquet_path, compression="SNAPPY")
    
    print(f"成功保存增強後的資料集至: {output_parquet_path}")
    print(f"檔案大小: {os.path.getsize(output_parquet_path) / (1024*1024):.2f} MB")
    
    # 執行與測試數據生命週期降採樣歸檔管理
    from phm_pipeline import DataLifecycleManager
    archived_parquet_path = output_parquet_path.replace(".parquet", "_archived.parquet")
    if os.path.exists(archived_parquet_path):
        try:
            os.remove(archived_parquet_path)
        except Exception:
            pass
            
    print("\n[DATA LIFECYCLE] 執行增強資料庫生命週期管理測試...")
    lifecycle_mgr = DataLifecycleManager()
    lifecycle_mgr.archive_parquet_file(output_parquet_path, archived_parquet_path)
    
if __name__ == "__main__":
    augment_dataset()
