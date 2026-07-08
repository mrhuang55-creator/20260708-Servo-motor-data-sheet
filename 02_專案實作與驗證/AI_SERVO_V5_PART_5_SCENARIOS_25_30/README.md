# AI SERVO 伺服平台企業版 V5 — Part 5

故障場景 25–30

## 核心模組
- AI 診斷引擎 (`ai_engine.py`)
- 性能尋優器 (`performance_optimizer.py`)
- MR Configurator2 工作流引擎 (`mr_configurator2_workflow_engine.py`)
- MR-J5 參數回饋矩陣 (`mr_j5_parameter_feedback_matrix.csv`)
- 機械診斷決策矩陣 (`mechanical_diagnosis_matrix.csv`)

## 工作流程
MR-J5 / PLC / 感測器日誌 → AI 診斷引擎 → 根本原因分析 → 性能尋優器 → MR-J5 參數變更提案 → MR Configurator2 工作流 → 設定參數 → 試運轉 → KPI 對比評估 → 存檔

## 環境建置 (Environment Setup)
> [!NOTE]
> `venv` 目錄已被排除於 Git 版本控制之外，以避免跨平台二進位檔相容性問題與絕對路徑衝突。請按照以下步驟建立您的本地環境：

```bash
# 1. 建立虛擬環境
python -m venv venv

# 2. 啟用虛擬環境
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. 安裝相依套件
pip install -r requirements.txt
```

## 使用方式
```bash
# 1. 執行 AI 診斷引擎進行根本原因分析
python ai_engine.py --csv sample_servo_log.csv --out ai_engine_result.json

# 2. 執行性能尋優器產生參數調整提案
python performance_optimizer.py --ai_result ai_engine_result.json --out optimizer_recommendation.json

# 3. 執行工作流引擎產出符合 MR Configurator2 的設定檔
python mr_configurator2_workflow_engine.py --recommendation optimizer_recommendation.json --out mr_configurator2_workflow.json
```
