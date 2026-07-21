# 解決資料缺乏與實體現場驗證之修正計畫書

本計畫書旨在解決 AI Servo PHM 系統在向「實體工業現場部署」過渡時面臨的真實數據缺乏問題。藉由建構實體數據採集鏈路、引入實際電學/機械解析算法、以及優化 SLMP 實體 PLC 對接模組，實現從統計模擬向實體物理數據的混合驗證過渡。

## User Review Required

> [!IMPORTANT]
> 1. **測試台物理防護與急停安全性**：在進行「實體增益寫入驗證」時，必須確保實體 PLC 具備獨立的雙重硬體極限安全開關與 STO (Safe Torque Off) 迴路，防止軟體閉環參數錯誤寫入時造成的機械二次撞擊。
> 2. **現場通訊帶寬與採樣抖動**：三菱 MR-J5 透過 CC-Link IE TSN 通訊時，1ms (1000Hz) 頻率下連續採樣 121 個 Tags 可能會對網路頻寬產生負載，需配置網路 QoS 優先級等級 7（最高級）。

---

## Open Questions

> [!WARNING]
> 1. **硬體採樣通道完備性**：現場實體馬達驅動器是否已加裝加速度感測器 (Vibration Sensor)？若無，系統將需要退化使用「電流估算轉矩紋波」來替代物理加速度特徵。
> 2. **網路流量鏡像權限**：現場工業交換機是否支持 Port Mirroring 鏡像功能，以便我們採集真實封包軌跡 (PCAP) 來訓練網路丟包診斷分類器？

---

## Proposed Changes

為了將系統升級為支持真實數據採集與物理特徵解算，我們規劃修改以下模組：

### 1. 邊緣端物理訊號解調與特徵工程

#### [MODIFY] [dsp_analytics.py](file:///d:/20260713/20260707-馬達專題-V4/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/dsp_analytics.py)
*   **修改內容**：
    - 新增 `envelope_demodulation` 函數，使用希爾伯特變換 (Hilbert Transform) 對實測 20kHz 振動波形進行包絡解調，以精確提取實體軸承點蝕頻率（BPFO/BPFI）特徵。
    - 擴充 `BodeResponseAnalyzer`，支援輸入實體掃頻 (Swept Sine) 電流與轉速序列，動態解算並導出實體相位裕度 (Phase Margin) 與增益裕度。

#### [MODIFY] [phm_soft_sensors.py](file:///d:/20260713/20260707-馬達專題-V4/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/phm_soft_sensors.py)
*   **修改內容**：
    - 優化複數尤拉運算，在計算 `current_unbalance_pct` 時，加入低通數字濾波器過濾實體變頻器載波諧波噪訊，防止負序電流比率指標在載波波動下頻繁假警報。

---

### 2. 實體通信閉環與 PLC 對接模組

#### [MODIFY] [slmp_client.py](file:///d:/20260713/20260707-馬達專題-V4/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/slmp_client.py)
*   **修改內容**：
    - 將原本的 Mock 暫存器映射，修改為適應三菱 Q/L/R 系列 PLC 以及 MR-J5-A (SLMP 模式) 的**實體 Device 暫存器位址映射表**（例如：將參數映射至實體 D、W、或 ZR 暫存器區段）。
    - 引入網絡重試與超時自動降級機制，在實測丟包率大於 5% 時暫停閉環調整。

---

### 3. AutoML 數據管線與混合訓練

#### [MODIFY] [phm_pipeline.py](file:///d:/20260713/20260707-馬達專題-V4/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/phm_pipeline.py)
*   **修改內容**：
    - 擴充數據加載層，新增 `load_field_csv_data` 模組，支持讀取現場收集的真實 CSV/Parquet 數據。
    - 在機器學習訓練中實施**遷移學習 (Domain Adaptation)**：將模擬生成數據（源域）與部分採集到的現場實體數據（目標域）進行聯合對齊訓練，提升模型在現場噪訊下的分類鲁棒性。

---

## Verification Plan

### Automated Tests
*   **單元測試驗證**：
    - 執行 `python test_dsp_analytics.py`，驗證包絡解調在含噪混疊信號下的特徵提取精度。
    - 運行 `python test_slmp_closed_loop.py`，在模擬網路丟包與超時狀態下，驗證 SLMP 客戶端之自動重試與超時降級功能。

### Manual Verification
*   **現場通信互對接聯調**：
    - 將 `SLMPClient` 連接至實驗室實體三菱 PLC/驅動器，執行批次暫存器讀寫（`0x0401` 與 `0x1401`），確認實體傳輸時延低於 5ms 且無資安校驗失敗 (INTEGRITY_VIOLATION)。
*   **控制安全性手動測試**：
    - 手動注入異常電流，驗證一鍵急停減速控制字寫入速度與馬達實體停止時間，確認安全回滾完全閉環。
