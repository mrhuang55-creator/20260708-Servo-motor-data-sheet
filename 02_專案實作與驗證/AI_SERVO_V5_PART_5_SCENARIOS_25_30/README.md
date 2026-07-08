# AI SERVO Platform Enterprise V5 — Part 5

Scenario 25–30

## Modules
- AI Engine
- Performance Optimizer
- MR Configurator2 Workflow Engine
- MR-J5 parameter feedback matrix
- Mechanical diagnosis matrix

## Workflow
MR-J5 / PLC / Sensor Log → AI Engine → Root Cause Diagnosis → Performance Optimizer → MR-J5 Parameter Proposal → MR Configurator2 Workflow → Set → Trial → KPI Compare → Save

## Environment Setup
> [!NOTE]
> The `venv` directory is excluded from Git to prevent cross-platform binary compatibility issues and absolute path conflicts. Please set up your local environment using the following steps:

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install required packages
pip install -r requirements.txt
```

## Usage
```bash
python ai_engine.py --csv sample_servo_log.csv --out ai_engine_result.json
python performance_optimizer.py --ai_result ai_engine_result.json --out optimizer_recommendation.json
python mr_configurator2_workflow_engine.py --recommendation optimizer_recommendation.json --out mr_configurator2_workflow.json
```
