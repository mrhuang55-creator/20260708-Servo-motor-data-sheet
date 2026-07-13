# 伺服系統進階故障場景（Scenario 25–30）對話與開發紀錄說明 (conversation_history.md)

本文件完整記錄了工業 AI 系統架構師與 AI 資深開發工程師針對本專案的對話需求、開發設計思維以及最終的規格指標。

---

## 1. 架構師與工程師對話歷史摘要

### 1.1 階段一：進階故障特徵分析與標籤映射 (架構設計)
*   **需求背景**：針對 1000Hz 高頻伺服感測數據，識別 Resonance (共振)、Gain Instability (增益不穩定)、Brake Failure (煞車失效)、Emergency Stop (緊急停止)、Combined Fault (複合故障)、Progressive Failure (漸進式失效)。
*   **數據規範**：優先分析 121 個 Tags，特別是位置殘差、電流不平衡、振動頻率響應與通訊封包流失率。
*   **核心演算法與公式**：
    - **頻域分析 (Scenario 25-26)**：分析 100Hz 以上的和諧波特徵，利用滑動 FFT 和 Peak Prominence 公式進行判定。
    - **時域滾動視窗 (Scenario 30)**：追蹤 `normal` -> `early_degradation` -> `severe_warning` -> `trip` 的健康度狀態轉變軌跡。
    - **互相關分析 (Scenario 29)**：強制分析通訊同步誤差與馬達轉矩負載的互相關（Cross-Correlation）以確定因果關係。
    - **邏輯斷言防誤警**：若 Packet Loss > 2.0% 且 Position Error > 100 脈衝，優先判斷為「通訊導致失控」，排除真機械卡死誤報。
*   **產出物**：
    - 建立了 `advanced_fault_diagnosis_matrix.md` 規格書。
    - 更新了 `ai_engine.py` 診斷核心程式。
    - 更新了 `performance_optimizer.py` 與 `mr_configurator2_workflow_engine.py` 邏輯。

### 1.2 階段二：大數據、特徵工程與模型訓練 (開發執行)
*   **需求背景**：協助執行馬達 PHM 後續操作，編寫大數據串流 Parquet 寫入、殘差特徵提取、剛性規則與 ML 注意力的混和分類器、以及 RandomForest 模型訓練與含噪訊的泛化性壓力測試。
*   **實作細節**：
    - 建立 `phm_pipeline.py`。
    - 分塊追加寫入 10,000,000 筆資料至 `streaming_data.parquet`，解決記憶體 OOM 問題。
    - 實作位置、速度、轉矩、溫度與通訊等 5 項物理殘差。
    - 訓練 `y_stage` 與 `y_trip_soon` RandomForest 分類模型，並注入高斯雜訊與偏移進行壓力測試。
*   **產出物**：
    - 建立了 `phm_pipeline.py` 管線腳本。
    - 產生了 10M 筆 Parquet 大數據檔案。
    - 撰寫了 `walkthrough.md` 完整的 Spec Validation 規格驗證報告。

### 1.3 階段三：分段式流式運算與優化 (效能與自適應優化)
*   **需求背景**：針對 10M 筆大數據進行分段生成以優化 Token 與邊緣端記憶體開銷，設計增量驗證、條件式回饋 Early Stopping 以及過擬合自適應機制。
*   **實作細節**：
    - **Staged Streaming**：使用 Python Generator 模式，分塊（每塊 1M 筆）追加寫入資料，免除 OOM 風險。
    - **Incremental Validation**：每完成 1M 筆對關鍵欄位進行均值與變異數包絡線檢查，保證資料無偏移。
    - **Conditional Feedback**：利用 `warm_start` 增量微調隨機森林。當預警模型精度達標（如 97.82% >= 97.0%），立即終止訓練，使模型極度輕量化（0.13MB）。
    - **自適應過擬合檢測**：若 Train 與 Val 準確率差距 > 10%，自動降級 `max_depth` 並重新訓練。
    - **閉環輸出**：在指令最末段自動生成符合三菱電機格式的 `ai_engine_result.json`、`optimizer_recommendation.json` 與 `mr_configurator2_workflow.json` 以進行閉環對接。
*   **產出物**：
    - 建立了 `system_instructions.md` 供 pipeline 自動調用。
    - 在 `log.md` 與 `walkthrough.md` 中寫入了混淆矩陣與泛化報告。

### 1.4 階段四：參數物理映射與 SLMP 通信閉環 (聯調與控制安全)
*   **需求背景**：對齊三菱伺服驅動器暫存器架構，針對摩擦力與背隙進行物理補償優化，並實作 MC 3E 通信協定閉環調參，同時確保現場通訊異常時的安全停機與回滾（Rollback）機制。
*   **實作細節**：
    - **參數映射**：擴充 `performance_optimizer.py`，將故障診斷結果映射至 `PE02`（摩擦力補償，以估計之摩擦扭矩 `friction_estimate_nm` * 100.0 換算）及 `PE07`（遺失運動/反向間隙補償，補償 80% 穩態間隙 `encoder_drift_pulse` * 0.8）。
    - **MC 3E 通信**：在 `slmp_client.py` 實作二進位協定客戶端 `SLMPClient`（支援 `0x0401` 批次讀取與 `0x1401` 批次寫入）與模擬伺服器 `SLMPServerMock`（TCP 5007 埠）。
    - **多軸 TSN 路由**：客戶端支援 Network ID、PC No、I/O No 與 Station No 多層路由尋址。
    - **防抖過濾器**：實作 `check_anti_chatter_current` 計算滑動均值電流，防止單點瞬時雜訊誤觸回滾。
    - **安全急停與回滾**：當偵測到連續異常電流違規，系統在回滾前自動執行安全減速控制（`1200rpm -> 600rpm -> 0rpm`），確認馬達完全靜止（進入安全 STO 狀態）後，才寫入備份參數暫存器進行 Rollback。
*   **產出物**：
    - 建立了 `slmp_client.py` 通訊模組。
    - 建立了 `test_slmp_closed_loop.py` 聯調與安全回滾驗證腳本。

### 1.5 階段五：演算法特徵升級與不平衡學習整合 (痛點突破)
*   **需求背景**：經專家評估，排除不對齊的 `Sup data` 整合。確定主線 106 GB 資料之核心痛點為「早期退化 (LO) 類別樣本偏少」與「LN 正常/LO 早期退化物理訊號高度重疊（可分性低）」。
*   **實作細節**：
    - **特徵升級**：在 `dsp_analytics.py` 實作時域高階特徵（峭度 Kurtosis、波峰因數 Crest Factor、裕度因數 Margin Factor），成功在 LO 狀態下將峭度自 LN 基線的 3.0 飄升至 26.8560，解決特徵重疊問題。
    - **不平衡學習**：在 `ml_automl_engine.py` 實作 Fold 內部過採樣函數 (SMOTE-like) 及代價敏感權重機制。在極低（3%）少數類 LO 測試中將模型的 Macro F1-Score 提升至 0.5395。
*   **產出物**：
    - 升級了 `dsp_analytics.py` 特徵提取與 `ml_automl_engine.py` 模型訓練平台。
    - 建立了 `test_sup_data_integration.py`（作為 scratch 驗證）與更新了所有測試單元。

---

## 2. 核心代碼設計原理說明

### 2.1 物理殘差公式 (Digital Twin Residuals)
在 `phm_pipeline.py` 中，計算實際值與預測值的差值來提取故障殘差特徵：
- **位置殘差**：$\text{residual\_position} = \text{pos\_residual} - 0.7 \times \text{following\_error}$
- **溫度溫差**：$\text{residual\_thermal} = T_{\text{motor}} - T_{\text{drive}}$

### 2.2 防誤判邏輯斷言 (Mitigation Rule)
```python
if row["ethercat_packet_loss_pct"] > 2.0 and row["following_error_abs_pulse"] > 100.0:
    return "communication_loss_of_control"
```
此邏輯在 `ai_engine.py` 與 `phm_pipeline.py` 的 `hybrid_classifier` 中均已強制實現。

### 2.3 防抖與安全回滾控制邏輯 (Anti-Chatter & Safe Deceleration)
- **防抖滑動平均公式**：
  $$\text{SMA}_{\text{current}} = \frac{1}{W} \sum_{i=t-W+1}^{t} I_i$$
  當連續視窗 $W$ 的平均電流 $\text{SMA}_{\text{current}} > \text{threshold}$，判斷為真故障，排除單點噪訊。
- **安全停機狀態機**：
  $$\text{Speed}_{\text{cmd}} = \begin{cases} 1200 \text{ rpm} & t = 0 \\ 600 \text{ rpm} & t = 1 \\ 0 \text{ rpm} & t = 2 \text{ (確認靜止，進入安全 STO 狀態)} \end{cases}$$

---

## 3. 專案規格指標 (Spec Validation Report)
*   **總行數**：**10,000,000** 筆資料（已達標）。
*   **模型大小**：`y_stage` 約 **2.87 MB**，`y_trip_soon` 約 **0.099 MB**（具備優異的邊緣端部署性能）。
*   **Scenarios 診斷 Recall**：Scenario 02, 04, 26, 29, 30 均達到 **100.00%**。
*   **y_trip_soon (停機預警) 泛化指標**：精準率 **98.66%** / 召回率 **85.62%** / F1-Score **91.68%**。
*   **防誤警斷言機制成功率**：在 1,976 筆噪訊干擾測試樣本中，攔截覆蓋率達到 **100.0%**。
*   **y_stage 混淆矩陣 (Confusion Matrix)**：
    ```text
    [3737  265    0    0]  (正常 LN)
    [ 565 15756  356    0]  (早期衰退 LO)
    [   0  795 2380    3]  (嚴重警告 MED)
    [   0    0  110 2033]  (停機警告 HI)
    ```
