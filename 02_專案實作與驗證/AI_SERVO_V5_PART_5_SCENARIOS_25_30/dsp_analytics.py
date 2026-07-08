#!/usr/bin/env python3
import numpy as np

class KalmanFilter2D:
    """
    2D 卡爾曼估測器
    狀態向量: x = [位置, 速度]^T
    量測值: z = 實際編碼器位置
    """
    def __init__(self, dt=0.001, q_cov=0.01, r_cov=1.0):
        self.dt = dt
        # 狀態轉移矩陣 F
        self.F = np.array([
            [1.0, self.dt],
            [0.0, 1.0]
        ])
        # 量測矩陣 H
        self.H = np.array([[1.0, 0.0]])
        
        # 雜訊協方差矩陣
        self.Q = np.array([
            [q_cov * (dt**3)/3.0, q_cov * (dt**2)/2.0],
            [q_cov * (dt**2)/2.0, q_cov * dt]
        ])
        self.R = np.array([[r_cov]])
        
        # 狀態值與協方差初始設定
        self.x = np.array([[0.0], [0.0]])
        self.P = np.array([
            [1.0, 0.0],
            [0.0, 1.0]
        ])
        
    def reset(self, initial_position=0.0, initial_velocity=0.0):
        self.x = np.array([[initial_position], [initial_velocity]])
        self.P = np.array([
            [1.0, 0.0],
            [0.0, 1.0]
        ])
        
    def predict(self):
        # 預測狀態: x_k|k-1 = F * x_k-1
        self.x = np.dot(self.F, self.x)
        # 預測協方差: P_k|k-1 = F * P_k-1 * F^T + Q
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return self.x
        
    def update(self, measurement_pos):
        # 量測更新: K = P * H^T * (H * P * H^T + R)^-1
        z = np.array([[measurement_pos]])
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        
        # x_k|k = x_k|k-1 + K * (z - H * x_k|k-1)
        residual = z - np.dot(self.H, self.x)
        self.x = self.x + np.dot(K, residual)
        
        # P_k|k = (I - K * H) * P_k|k-1
        I = np.eye(2)
        self.P = np.dot(I - np.dot(K, self.H), self.P)
        return self.x

class BodeResponseAnalyzer:
    """
    波德圖頻譜響應與共振峰分析器
    """
    def __init__(self, sampling_rate_hz=1000):
        self.fs = sampling_rate_hz
        
    def analyze(self, cmd_pos, act_pos):
        """
        計算幅頻與相頻響應，並定位共振峰與系統相位/增益邊界
        """
        n = len(cmd_pos)
        if n < 64:
            return {"status": "error", "message": "Signal length too short"}
            
        # 頻域轉換 FFT
        fft_cmd = np.fft.rfft(cmd_pos)
        fft_act = np.fft.rfft(act_pos)
        freqs = np.fft.rfftfreq(n, d=1.0/self.fs)
        
        # 計算傳遞函數 G(f) = Act(f) / Cmd(f)
        # 避免除以 0
        eps = 1e-8
        g_f = fft_act / (fft_cmd + eps)
        
        # 幅度響應 (dB)
        mag_db = 20 * np.log10(np.abs(g_f) + eps)
        # 相位響應 (degrees)
        phase_deg = np.angle(g_f) * 180.0 / np.pi
        
        # Nyquist 實部與虛部
        real_gf = np.real(g_f)
        imag_gf = np.imag(g_f)
        
        # 定位高頻共振峰 (>100Hz)
        idx_high = (freqs >= 100.0)
        peak_freq = 0.0
        peak_prominence = 0.0
        
        if np.any(idx_high):
            high_freqs = freqs[idx_high]
            high_mag = mag_db[idx_high]
            
            # 簡易計算峰值與局部均值的突出度
            # 局部視窗均值
            mean_mag = np.mean(high_mag)
            peak_idx = np.argmax(high_mag)
            
            peak_freq = float(high_freqs[peak_idx])
            peak_prominence = float(high_mag[peak_idx] - mean_mag)
            
        # 計算增益邊界與相位邊界 (簡易估計)
        # 相位為 -180 度處的增益，增益為 0 dB 處的相位裕度
        phase_margin = 180.0
        gain_margin_db = 99.0
        
        # 尋找跨越 0dB 處的相位裕度
        idx_cross_gain = np.where(np.diff(np.sign(mag_db)))[0]
        if len(idx_cross_gain) > 0:
            phase_at_cross = phase_deg[idx_cross_gain[0]]
            phase_margin = float(phase_at_cross + 180.0)
            
        # 尋找跨越 -180度處的增益裕度
        idx_cross_phase = np.where(np.diff(np.sign(phase_deg + 180.0)))[0]
        if len(idx_cross_phase) > 0:
            gain_margin_db = float(-mag_db[idx_cross_phase[0]])
            
        return {
            "status": "success",
            "frequencies": freqs.tolist(),
            "magnitude_db": mag_db.tolist(),
            "phase_deg": phase_deg.tolist(),
            "nyquist_real": real_gf.tolist(),
            "nyquist_imag": imag_gf.tolist(),
            "resonance_peak_freq_hz": peak_freq,
            "resonance_prominence_db": peak_prominence,
            "phase_margin_deg": phase_margin,
            "gain_margin_db": gain_margin_db
        }

class ARIMAPredictor:
    """
    時間序列自迴歸溫升趨勢預測器 (簡化 ARIMA(1,1,0) 模型)
    方程式: (T_t - T_t-1) = phi * (T_t-1 - T_t-2) + error
    """
    def __init__(self):
        self.phi = 0.5 # 預設自迴歸係數
        
    def fit(self, temp_series):
        """
        利用最小平方法配適 phi 參數
        """
        if len(temp_series) < 5:
            return self.phi
            
        # 一階差分
        diff = np.diff(temp_series)
        X = diff[:-1]
        y = diff[1:]
        
        # phi = Cov(X,y) / Var(X)
        cov = np.cov(X, y)
        if cov.ndim == 2:
            self.phi = cov[0, 1] / (np.var(X) + 1e-8)
        else:
            self.phi = 0.5
            
        # 限幅防止不穩定
        self.phi = np.clip(self.phi, -0.9, 0.9)
        return self.phi
        
    def predict_future(self, temp_series, steps_ahead=30):
        """
        遞迴預估未來 steps_ahead 步數的溫度
        """
        if len(temp_series) < 3:
            return [temp_series[-1]] * steps_ahead
            
        predictions = []
        last_t = temp_series[-1]
        last_diff = temp_series[-1] - temp_series[-2]
        
        current_diff = last_diff
        current_t = last_t
        for _ in range(steps_ahead):
            # diff_k = phi * diff_k-1
            current_diff = self.phi * current_diff
            # T_k = T_k-1 + diff_k
            current_t = current_t + current_diff
            predictions.append(float(current_t))
            
        return predictions
