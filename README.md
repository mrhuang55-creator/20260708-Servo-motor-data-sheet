# AI Servo 伺服馬達預測性維護與閉環控制專案 (v7.1.0 綠色部署與安全硬化版)

本專案是一個針對工業級伺服馬達（如三菱電機 MR-J5 系列）所開發的**預測性維護 (PHM) 與閉環參數自動優化系統**。系統整合了高頻信號處理、AutoML 競賽平台、純 NumPy 手刻深度學習引擎，以及 SLMP (MC 3E) 二進位通訊協定，實現了從數據監控、故障診斷到參數補償的完整自動化閉環流程。

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
