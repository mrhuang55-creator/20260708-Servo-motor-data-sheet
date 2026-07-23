# AI Servo 伺服馬達預測性維護與閉環控制專案

本專案是一個針對工業級伺服馬達（如三菱電機 MR-J5 系列）所開發的**預測性維護 (PHM) 與閉環參數自動優化系統**。系統整合了高頻信號處理、AutoML 競賽平台、純 NumPy 手刻深度學習引擎，以及 SLMP (MC 3E) 二進位通訊協定，實現了從數據監控、故障診斷到參數補償的完整自動化閉環流程。

---

## 📂 專案目錄結構

本專案的目錄劃分如下：

*   **[01_藍圖與設計規格/](file:///d:/20260708-Servo-motor-data-sheet/01_藍圖與設計規格)**：包含白皮書、30個故障矩陣規格、前後端資料規格書、通訊暫存器對照表等設計藍圖。
*   **[02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/](file:///d:/20260708-Servo-motor-data-sheet/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30)**：核心 Python 實作原始碼，包含特徵提取、故障診斷模型、SLMP 閉環控制器等核心模組。
*   **[報告輸出/](file:///d:/20260708-Servo-motor-data-sheet/報告輸出)**：包含報告一鍵繪圖腳本（`generate_reports_charts.py`）與自動生成的專家分析圖表。
*   **[server.py](file:///d:/20260708-Servo-motor-data-sheet/server.py)**：全量符合 0723 前後端資料規格書之 FastAPI 伺服器，支援 19 個 `/api/v1/` 端點與 8 大 WebSocket 頻道推播。

---

## 🛠️ 核心模組介紹

1.  **實時串流與數位雙生診斷 (`phm_pipeline.py`)**：基於卡爾曼濾波進行 1ms 級位置/速度實時降噪，並計算數位雙生殘差（`digital_twin_pos_residual`）。
2.  **AutoML 與貝氏尋優 (`ml_automl_engine.py`)**：集成了多種機器學習模型（MLP, RF, GBDT）的 Stacking 分類與 RUL 壽命預測，並實作貝氏與遺傳演算法超參調諧。
3.  **手刻深度學習引擎 (`deep_learning_models.py`)**：在無第三方 DL 庫依賴下，手刻 `AutogradTensor` 與 Attention-BiGRU 結構。
4.  **SLMP 二進位閉環控制 (`slmp_client.py`)**：實作 MC 3E 幀，動態讀寫 D1000-D1099 暫存器，並在參數回寫前執行 STO 安全減速。
5.  **0723 工業級 API 服務器 (`server.py`)**：對齊 0723 規格書，支援 L1/L2/L3、SHAP 瀑布圖、SHA-256 Fallback 哈希鏈及主控制台 API。

---

## ⚡ 測試環境建置 (Environment Setup)

為了保持 Git 倉庫的輕量化，並避免平台專有二進位檔相容性與絕對路徑硬編碼的問題，本專案的虛擬環境目錄（如 `vm/`）已被排除於 Git 版本控制之外。

請依照以下步驟在您本地建立虛擬環境並安裝相依套件：

### Step 1. 建立虛擬環境
於專案根目錄下執行：
```bash
python -m venv vm
```

### Step 2. 啟用虛擬環境
*   **Windows**:
    ```bash
    .\vm\Scripts\activate
    ```
*   **Linux / macOS**:
    ```bash
    source vm/bin/activate
    ```

### Step 3. 安裝相依套件
專案的核心依賴已條列於 `requirements.txt`，請在啟用虛擬環境後執行：
```bash
pip install -r requirements.txt
```

---

## ⚙️ 快速執行測試

啟用虛擬環境並安裝依賴後，可以執行自動化測試腳本：

```bash
# 執行 0723 前後端規格 API 單元測試
python test_server_v1_api.py

# 切換至核心模組目錄執行演算法測試
cd 02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/

# 執行 AutoML 尋優測試
python test_ml_automl.py

# 執行深度學習引擎測試
python test_deep_learning.py

# 執行 SLMP 閉環模擬與安全回滾測試
python test_slmp_closed_loop.py
```
