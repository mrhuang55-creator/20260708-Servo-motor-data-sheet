# AI Servo 伺服馬達預測性維護與閉環控制專案 (v7.1.0 綠色部署與安全硬化版)

本專案是一個針對工業級伺服馬達（如三菱電機 MR-J5 系列）所開發的**預測性維護 (PHM) 與閉環參數自動優化系統**。系統整合了高頻信號處理、AutoML 競賽平台、純 NumPy 手刻深度學習引擎，以及 SLMP (MC 3E) 二進位通訊協定，實現了從數據監控、故障診斷到參數補償的完整自動化閉環流程。

---

## ⚠️ 目前系統狀態：Demo / Simulation 模式（部署前必讀）

本系統**目前以模擬資料模式（Simulation Mode）運行，尚未連接真實伺服馬達硬體，`server.py` 內大部分 `/api/v1/` 端點回傳的是模擬/隨機生成數據，而非真實 AI 模型推論結果**。以下是 2026-08-07 稽核後確認、上線前必須調整的已知限制：

| # | 項目 | 現況 | 待調整方向 |
| :-: | :--- | :--- | :--- |
| 1 | 核心演算法串接 | `演算法核心.pkl`（`RandomForestClassifier` x2，已訓練完成）存在於 `02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/`，但 `server.py` 從未 `pickle.load()` 載入或呼叫 `.predict()`；即時 API（如 `/api/v1/l1/realtime`）目前是 `random.gauss()` 模擬輸出 | 於 FastAPI 啟動時載入模型為全域單例，並建立即時特徵計算管線接上 `.predict()` |
| 2 | 特徵品質 | pkl 需要 158 維特徵，其中 **93 個（59%）為訓練資料生成階段以 `np.random.normal` 產生的雜訊佔位符**（`extra_feature_1`~`_93`，見 `phm_pipeline.py`），非真實物理量測 | 移除雜訊佔位特徵，改用真實感測器欄位重新設計特徵集 |
| 3 | 模型可信度 | 以現有 `test_repository/data/` 41 工況模擬資料回測：`clf_stage` 準確率 26.7%、`clf_trip` 準確率 83.7%，**均低於「永遠猜多數類別」的對照組**（32.3% / 88.4%），另發現 label 分級數（5 類）與模型訓練時（4 類）不一致 | 上線前需重新訓練並以同格式驗證集驗證，目前不建議接上會影響實際判斷的流程 |
| 4 | 原始訓練資料 | 原始約 2 億筆 raw sensor data 因容量過大已被清除，且從未受 git 版控保護（`.gitignore` 排除 `*.parquet`），**無法用 git 復原** | 若需重新訓練，須重新連接實體 MR-J5（SLMP MC 協議）收集資料，或確認是否有其他備份 |
| 5 | 歷史資料源切換 | 前端可切換「活化數據源」在 `test_repository/data/*.json` 41 工況歷史檔與實體馬達間選擇，但即時推論端點未實際讀取被選中檔案的內容 | 讓資料源切換真正影響推論輸入，而非僅顯示名稱 |

> 上述第 1～4 項待確認/待辦，第 2026-08-07 稽核與部分前端動態化修復紀錄詳見 [log.md](file:///d:/20260708-Servo-motor-data-sheet/log.md)。

---

## 🔑 測試帳號 (Test Accounts)

系統內建三種角色的預設測試帳號（首次啟動時由 `server.py` 自動寫入 `users.db`），可直接用於登入測試：

| 角色 (Role) | 帳號 (Username) | 密碼 (Password) | Operator ID | 權限摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator（管理者）** | `admin` | `admin123` | `Admin_01` | 全系統最高權限，含核准/拒絕參數變更、刪除測試檔案、使用者管理 |
| **Engineer（工程師）** | `engineer` | `engineer123` | `Engineer_01` | 切換測試數據源、提交參數修改提案、上傳 `.json`/`.csv` 測試檔 |
| **Operator（操作員）** | `operator` | `operator123` | `Operator_01` | 全站唯讀存取，可監控儀表板與提交維修回報，禁止數據源切換與模型推升 |

> ⚠️ 以上密碼為系統預設測試密碼，僅供內部 Demo/開發環境使用；正式部署前務必於 `admin/users` 頁面更換為高強度密碼。

---

## 🚀 GCP / Linux 遠端部署注意事項（2026-08-07 更新）

系統原本只在單機 Windows `.exe` 模式下測試過，這次配合 GCP Linux 主機（`systemd` + `phm-backend`/`phm-frontend` 兩個服務）重新部署時，修正並排除了以下問題：

| # | 問題 | 修正 |
| :-: | :--- | :--- |
| 1 | 後端監聽位址寫死 `127.0.0.1`（`launcher.py`，僅影響 Windows `.exe` 路徑），遠端連不進來 | 改為可用 `AI_SERVO_BIND_HOST` 環境變數覆寫，預設 `0.0.0.0`。Linux 端 `systemd` 本來就是 `--host 0.0.0.0` / `frontend/run_flask.py` 的 `host="0.0.0.0"`，不受影響 |
| 2 | 前端 12 個模板 JS 寫死 `http://127.0.0.1:8000`，瀏覽器端的 `127.0.0.1` 永遠代表使用者自己的電腦，前後端分離部署時所有即時 API 請求全部悄悄失敗 | 改用 `base.html` 全域 `window.FASTAPI_BASE`（依瀏覽器連線 hostname 動態組出） |
| 3 | `phm-frontend.service` 開機即 `ModuleNotFoundError: No module named 'httpx'`，陷入無限重啟迴圈（`restart counter` 一路衝到 80+），導致 5000 埠對外顯示 `ERR_CONNECTION_REFUSED` | `pip install httpx`；部署文件的套件清單已同步更新 |
| 4 | `frontend/run_flask.py` 用 `debug=True` 跑在對外公開的正式環境，未攔截例外會顯示可執行任意程式碼的 Werkzeug 除錯主控台，PIN 還會被印進 `journalctl` | 改為 `debug=False`（`frontend/run_flask.py` 與 `servormotor/frontend/run_flask.py` 皆已修正） |

**部署所需完整 pip 套件清單**（GCP 部署文件原清單漏了 `httpx`）：

```bash
pip install flask requests httpx fastapi uvicorn pydantic pandas numpy scikit-learn joblib
```

完整 GCP Linux 部署指令與排錯記錄詳見 [`GCP部署與專案升級操作說明.txt`](file:///d:/20260708-Servo-motor-data-sheet/GCP部署與專案升級操作說明.txt) 與 [`log.md`](file:///d:/20260708-Servo-motor-data-sheet/log.md)。

---

## 📂 專案目錄結構

本專案的目錄劃分如下：

*   **[test_repository/data/](file:///d:/20260708-Servo-motor-data-sheet/test_repository/data/)**：標準測試數據庫，包含 `scenario_01.json` ~ `scenario_30.json` 原始交付包 30 個情境檔、V6 全工況檔與全新客製化測試馬達檔 `scenario_31_custom_motor_test.json` 共 33 個測試檔案。
*   **[test_repository/models/](file:///d:/20260708-Servo-motor-data-sheet/test_repository/models/)**：模型權重與工況規則庫存放區。
*   **[dist/AI_Servo_Platform/](file:///d:/20260708-Servo-motor-data-sheet/dist/AI_Servo_Platform/)**：使用 PyInstaller 打包好的免安裝獨立可執行綠色軟體包，包含 [AI_Servo_Platform.exe](file:///d:/20260708-Servo-motor-data-sheet/dist/AI_Servo_Platform/AI_Servo_Platform.exe)。
*   **[01_藍圖與設計規格/](file:///d:/20260708-Servo-motor-data-sheet/01_藍圖與設計規格)**：包含白皮書、30個故障矩陣規格、前後端資料規格書、通訊暫存器對照表等設計藍圖。
*   **[02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30/](file:///d:/20260708-Servo-motor-data-sheet/02_專案實作與驗證/AI_SERVO_V5_PART_5_SCENARIOS_25_30)**：核心 Python 實作原始碼，包含特徵提取、故障診斷模型、SLMP 閉環控制器等核心模組。
*   **[server.py](file:///d:/20260708-Servo-motor-data-sheet/server.py)**：全量符合 0723 前後端資料規格書之 FastAPI/Flask 後端服務，支援 19 個 API 端點、8 大 WebSocket 頻道與 SQLite 持久化資料庫。

---

## 🛡️ 工業資安與系統安全機制 (Security & UX Features)

### 1. 三層級 RBAC 角色權限管控與檔案權限
*   **Operator (操作員)**：全站唯讀存取，禁止進行數據源切換、模型推升或上傳刪除動作。
*   **Engineer (工程師)**：具備切換測試數據源、提交參數修改提案與上傳 `.json` / `.csv` 測試檔之權限。
*   **Administrator (管理者)**：獨家擁有**核准/拒絕參數變更**與**刪除測試檔案**之最高權限。

### 2. 開啟新分頁/新視窗自動轉頁至登入區 (Auto-Redirect Gate)
*   採用 **W3C `sessionStorage` 單一分頁隔離憑證**。
*   當使用者開啟全新分頁或瀏覽器重新開啟時，系統偵測到無當前分頁活化憑證，會在 1 毫秒內以 `window.location.replace('/login')` **零延遲自動轉頁至帳號輸入區**，防止殘留於無法連線的工作頁面。

### 3. 特權角色 30 分鐘硬性絕對時間上限與第 28 分鐘 Quick 續期
*   **防範自動化腳本與忘記登出**：針對 Engineer / Admin 實作 30 分鐘硬性絕對時間上限。滿 30 分鐘伺服器端 Token 硬性失效 (401 Unauthorized)。
*   **第 28 分鐘對話框 Quick 續期**：第 28 分鐘（剩餘 120 秒）時，畫面上彈出 `privilegeTimeoutWarningModal` 提示框。工程師點擊`【無縫延長 30 分鐘】`即可零中斷無感續期；若 2 分鐘內無回應，自動強制登出並轉頁至 `/login`。

### 4. 審核事項 SQLite 數據庫硬化持久化 (SQLite Hardened Persistence)
*   管理者在 Admin Approvals 點擊「核准 (approve)」時，變更紀錄與寫入參數會 **100% `conn.commit()` 寫入 `admin_approvals.db` 硬碟資料庫**與 ISO 哈希鏈稽核日誌。
*   軟體重開或 `.exe` 重新執行後，已核准項目永久保存，**絕對不會復原**。

---

## ⚡ 測試環境與可執行檔執行 (Executable Packaging)

### 方式 A. 直接執行免安裝 `.exe` 可執行檔（推薦工廠現場）
無需安裝 Python 或任何套件，隨身碟複製即可直接執行：
```cmd
d:\20260708-Servo-motor-data-sheet\dist\AI_Servo_Platform\AI_Servo_Platform.exe
```
*   執行後將自動於背景監聽 Port 8000 (FastAPI) 與 Port 5000 (Flask)，並自動啟動瀏覽器開啟主頁面 `http://127.0.0.1:5000/login`。

### 方式 B. 於 Python 虛擬環境中執行
若需進行開發或修改原始碼，請使用專案內部的 `vm` 虛擬環境：
```bash
# 啟用 vm 虛擬環境
.\vm\Scripts\activate

# 啟動後端與前端 BFF 服務
python launcher.py

# 重新進行 PyInstaller 打包
python -m PyInstaller AI_Servo_Platform.spec --noconfirm
```
