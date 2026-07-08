#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime

def create_workflow(rec):
    return {
        "workflow_name": "MR-J5 AI Servo Parameter Set-Trial-Save",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "steps": [
            {"step": 1, "name": "Read current MR-J5 parameters", "output": "parameter_backup_before.json"},
            {"step": 2, "name": "Apply AI recommended trial parameters", "parameter_group": rec["mr_j5_parameter_group"], "parameter_writes": rec.get("mr_j5_parameter_writes", {}), "mode": "trial"},
            {"step": 3, "name": "Run low-speed verification", "condition": "stable motion, no trip, check current spike and following error"},
            {"step": 4, "name": "Run production-speed verification", "condition": "KPI improved and takt time acceptable"},
            {"step": 5, "name": "Collect after-tuning data", "kpi": rec["target_kpi"]},
            {"step": 6, "name": "Compare before/after KPI", "save_condition": rec["save_condition"]},
            {"step": 7, "name": "Save MR-J5 parameters / Rollback if failed", "tool": "MR Configurator2 parameter write/save"},
            {"step": 8, "name": "Generate tuning report", "output": "ai_servo_tuning_report.md"}
        ]
    }

def run_trial_safety_gate(rec, df_before, df_after):
    """
    執行試運行安全閘門判定 (Safety Gate/Trial Run)
    驗證點：
    1. 電流有無突波 (Current Spike): 最大電流不得超過 15.0A
    2. 追隨誤差 (Following Error) 是否惡化: 調整後的平均誤差不得大於調整前 (容許 2% 浮動)
    3. KPI 改善度: 目標 KPI 必須有至少一項改善 >= 10%
    """
    print("\n" + "="*60)
    print("        MR-J5 試運行安全閘門驗證 (Safety Gate Verification)")
    print("="*60)
    
    # 1. 電流突波檢查
    max_current_after = float(df_after["current_rms_a"].max())
    current_spike_violation = max_current_after > 15.0
    print(f"  [電流突波檢查] 試運轉最大電流: {max_current_after:.2f} A | 門檻值: 15.00 A | {'不通過 (VIOLATION)' if current_spike_violation else '通過 (PASS)'}")
    
    # 2. 追隨誤差惡化檢查
    fe_mean_before = float(df_before["following_error_abs_pulse"].mean())
    fe_mean_after = float(df_after["following_error_abs_pulse"].mean())
    # 容許微小浮動，若惡化超過 2% 則判定為不通過
    fe_degradation_violation = fe_mean_after > (fe_mean_before * 1.02)
    print(f"  [誤差惡化檢查] 調機前誤差: {fe_mean_before:.2f} | 調機後誤差: {fe_mean_after:.2f} | {'不通過 (VIOLATION)' if fe_degradation_violation else '通過 (PASS)'}")
    
    # 3. KPI 改善判定
    target_kpis = rec.get("target_kpi", [])
    kpi_improvements = {}
    any_improved = False
    
    print("  [KPI 改善指標對比]:")
    for kpi in target_kpis:
        if kpi not in df_before.columns or kpi not in df_after.columns:
            continue
        val_before = float(df_before[kpi].mean())
        val_after = float(df_after[kpi].mean())
        
        # 針對 health_index，越高越好；其他指標越低越好
        if kpi == "health_index":
            improvement = (val_after - val_before) / (val_before + 1e-8)
        else:
            improvement = (val_before - val_after) / (val_before + 1e-8)
            
        kpi_improvements[kpi] = improvement
        is_imp = improvement >= 0.10
        if is_imp:
            any_improved = True
        print(f"    - {kpi}: 調機前={val_before:.2f} -> 調機後={val_after:.2f} | 改善幅度: {improvement*100:.2f}% | 狀態: {'達標' if is_imp else '未達標'}")
        
    kpi_check_passed = any_improved or len(target_kpis) == 0
    print(f"  [KPI 改善總評] 至少一項改善 >= 10%: {'通過 (PASS)' if kpi_check_passed else '不通過 (VIOLATION)'}")
    
    # 總結判定
    safety_passed = (not current_spike_violation) and (not fe_degradation_violation) and kpi_check_passed
    
    if safety_passed:
        print("\n  >> [驗證結論] 試運行安全閘門通過 (Safety Gate Passed)！建議正式寫入 ROM。")
        print("  >> [執行動作] 提交並儲存三菱參數 (COMMIT & SAVE).")
        action_result = "COMMIT"
    else:
        print("\n  >> [警告 WARNING] 試運行未通過安全指標或 KPI 未有明顯改善！")
        print("  >> [執行動作] 啟動 Rollback 機制，還原為原始備份參數。")
        action_result = "ROLLBACK"
    print("="*60 + "\n")
    
    return safety_passed, action_result

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--recommendation", required=True)
    p.add_argument("--out", default="mr_configurator2_workflow.json")
    a = p.parse_args()
    rec = json.loads(Path(a.recommendation).read_text(encoding="utf-8"))
    wf = create_workflow(rec)
    Path(a.out).write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(wf, indent=2, ensure_ascii=False))
