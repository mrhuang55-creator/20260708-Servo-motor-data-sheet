#!/usr/bin/env python3
import numpy as np
from dsp_analytics import KalmanFilter2D, BodeResponseAnalyzer, ARIMAPredictor

def test_kalman_filter():
    print(">>> 測試 1.1：2D 卡爾曼估測器 (Kalman Filter)...")
    kf = KalmanFilter2D(dt=0.001, q_cov=10000000.0, r_cov=5.0)
    
    # 建立一個真實正弦位置軌跡與加入雜訊的觀測值
    t = np.linspace(0, 1.0, 1000)
    true_pos = 100.0 * np.sin(2 * np.pi * 5.0 * t) # 5Hz 正弦波
    noisy_pos = true_pos + np.random.normal(0, 5.0, len(t))
    
    filtered_pos = []
    filtered_speed = []
    
    kf.reset(initial_position=noisy_pos[0])
    for z in noisy_pos:
        kf.predict()
        x_state = kf.update(z)
        filtered_pos.append(x_state[0, 0])
        filtered_speed.append(x_state[1, 0])
        
    rmse_before = np.sqrt(np.mean((noisy_pos[500:] - true_pos[500:])**2))
    rmse_after = np.sqrt(np.mean((np.array(filtered_pos)[500:] - true_pos[500:])**2))
    
    print(f"  雜訊原始偏差 RMSE: {rmse_before:.4f}")
    print(f"  濾波降噪後偏差 RMSE: {rmse_after:.4f}")
    assert rmse_after < rmse_before, "卡爾曼濾波效果不佳！"
    print("  [PASS] 2D 卡爾曼估測器降噪測試通過！")

def test_bode_analyzer():
    print("\n>>> 測試 1.2：波德圖頻譜與共振峰分析器 (Bode Analyzer)...")
    analyzer = BodeResponseAnalyzer(sampling_rate_hz=1000)
    
    # 建立掃頻信號 (Swept Sine) 10Hz 至 400Hz
    t = np.linspace(0, 1.0, 1000)
    # 指令位置
    cmd = np.sin(2 * np.pi * (10 + 190 * t) * t)
    
    # 模擬系統帶有 290Hz 共振的響應
    # 建立共振響應: 在 290Hz 處振幅放大
    act = cmd.copy()
    # 注入一個強共振頻率
    resonance_noise = 2.5 * np.sin(2 * np.pi * 290.0 * t)
    act += resonance_noise
    
    res = analyzer.analyze(cmd, act)
    
    print(f"  分析狀態: {res['status']}")
    print(f"  共振峰頻率: {res['resonance_peak_freq_hz']:.2f} Hz (目標: ~290.0 Hz)")
    print(f"  共振突出度: {res['resonance_prominence_db']:.2f} dB")
    print(f"  增益裕度: {res['gain_margin_db']:.2f} dB")
    print(f"  相位裕度: {res['phase_margin_deg']:.2f} 度")
    
    assert abs(res['resonance_peak_freq_hz'] - 290.0) < 15.0, "共振峰分析誤差過大！"
    assert "nyquist_real" in res and "nyquist_imag" in res, "Nyquist 實部與虛部計算缺失！"
    print(f"  Nyquist 實部樣本[5]: {res['nyquist_real'][5]:.4f} | 虛部樣本[5]: {res['nyquist_imag'][5]:.4f}")
    print("  [PASS] 波德圖與共振峰頻譜分析測試通過！")

def test_arima_predictor():
    print("\n>>> 測試 1.3：長時溫升預測自迴歸模型 (ARIMA)...")
    predictor = ARIMAPredictor()
    
    # 建立一個緩慢升溫的對數曲線數據
    t = np.arange(100)
    # 模擬從 50度上升，趨於平緩但仍緩慢增長
    temp = 50.0 + 15.0 * np.log1p(t) + np.random.normal(0, 0.1, len(t))
    
    # 配適模型
    phi = predictor.fit(temp)
    print(f"  估計的 AR(1) 係數 phi: {phi:.4f}")
    
    # 預測未來 30 步的溫度
    preds = predictor.predict_future(temp, steps_ahead=30)
    
    print(f"  最後觀測溫度: {temp[-1]:.2f} °C")
    print(f"  預測未來 10 步溫度: {preds[9]:.2f} °C")
    print(f"  預測未來 30 步溫度: {preds[29]:.2f} °C")
    
    # 溫度應維持溫和上升或平緩趨勢，且長時預估不可發散
    assert abs(preds[-1]) < 150.0, "ARIMA 預估結果發散！"
    print("  [PASS] ARIMA 溫升趨勢預估測試通過！")

if __name__ == "__main__":
    test_kalman_filter()
    test_bode_analyzer()
    test_arima_predictor()
