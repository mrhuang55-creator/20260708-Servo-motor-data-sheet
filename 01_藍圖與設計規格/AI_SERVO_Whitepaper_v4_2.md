# AI Servo Data Analysis, Feedback Control and Parameter Tuning Whitepaper

## 1. 目的
本白皮書把 Servo AI Dataset v4.1 延伸成完整的 **AI Servo 閉環改善流程**。目標不是只做資料分析，而是把 HMI、PLC、Servo Drive、Motor、Encoder、EtherCAT/CC-Link、Vision AOI、Robot 與 I/O 資料整合後，產生可被工程師審核的三菱伺服參數調整建議。

> 安全原則：AI 不直接無條件寫入 Servo 參數。AI 只提出建議、風險等級、驗證方法與回復點；實際寫入必須由授權工程師確認。

## 2. 參考依據
Mitsubishi Electric MR-J5 調整手冊說明 quick tuning 會以振動扭矩取得響應，並調整各增益與機械共振抑制濾波器；官方參數手冊則涵蓋參數、調整、故障原因與警告等用途。本白皮書採用「通用工程分類 + 模擬資料集」方式，不複製原廠專有參數表。參數號碼與可用範圍應依現場 MR-J4/MR-J5 實際型號手冊確認。

## 3. 通訊串接資料架構

核心資料流：

1. Servo Drive 回傳 position、speed、torque、current、voltage、temperature、alarm。
2. Motor/Encoder/Sensor 提供 encoder、bearing temperature、vibration XYZ、limit sensor。
3. PLC/Motion Controller 提供 step、recipe、command id、scan time、interlock。
4. HMI/SCADA 顯示 AI 結果，讓工程師 approve/reject。
5. AI Engine 執行 anomaly detection、RUL、Digital Twin residual、FFT/BPFO/BPFI 分析。
6. 通過安全閘門後，才允許 controlled write 到 Servo parameter。

![Connection Architecture](figures/connection_architecture_hmi_plc_servo_motor.png)

## 4. AI Servo 閉環流程

![AI Servo Feedback Loop](figures/ai_servo_feedback_loop.png)

流程分為：資料收集、清理對齊、特徵工程、模型診斷、參數建議、安全審核、低速試跑、驗證、部署與監控。

## 5. 資料分析後的處理

### 5.1 診斷輸出
AI 分析結果至少輸出：

- fault_category
- fault_type
- fault_stage
- anomaly_score
- health_index
- failure_probability
- RUL seconds / RUL cycles
- predictive_maintenance_label
- root_cause
- parameter proposal
- risk level
- validation procedure

### 5.2 性能提升 KPI

| KPI | 改善方向 | 對應資料 |
|---|---|---|
| Settling time | 縮短定位後穩定時間 | position_error, vibration_rms |
| Following error | 降低命令與實際位置誤差 | position_error_pulse |
| Cycle time | 縮短單次動作週期 | plc_step_no, motion_complete |
| Current margin | 降低過電流風險 | current_rms_a, current_limit_pct |
| Thermal margin | 降低馬達/驅動器溫升 | motor_temp_c, drive_temp_c |
| Vibration margin | 降低共振與軸承風險 | FFT, BPFO, BPFI, BSF, FTF |
| Quality stability | AOI/定位品質提升 | vision_alignment_score, aoi_pass_flag |

## 6. 三菱 Servo 參數調整矩陣

![Parameter Impact Risk](figures/servo_parameter_impact_risk_chart.png)

> 注意：下表採用 Mitsubishi-style 參數群概念。實際參數編號、名稱、範圍與單位請依 MR-J4/MR-J5 對應型號手冊確認。

| Parameter Group             | Example Mitsubishi-style Parameter                      | Purpose                                   | AI Trigger                                        | Direction of Change                                            | Risk   | Validation                            |
|:----------------------------|:--------------------------------------------------------|:------------------------------------------|:--------------------------------------------------|:---------------------------------------------------------------|:-------|:--------------------------------------|
| Backup / restore            | Parameter backup, amplifier copy, project version       | Create rollback point before tuning       | Any AI write recommendation                       | Backup first, no tuning yet                                    | Low    | Compare checksum and parameter export |
| Auto tuning                 | Real-time auto tuning / quick tuning / one-touch tuning | Estimate inertia and basic gains          | New equipment, changed load, high following error | Run tuning routine under safe mode                             | Medium | Dry run at low speed                  |
| Response level              | Machine response / auto tuning response                 | Improve settling time                     | Long settling, low vibration                      | Increase gradually                                             | Medium | Check overshoot and current margin    |
| Position loop gain          | Position gain / model loop gain                         | Reduce position error                     | High following_error_abs_pulse                    | Increase small step                                            | High   | Check oscillation and encoder noise   |
| Speed loop gain             | Speed gain                                              | Reduce speed tracking error               | speed_error_rpm high                              | Increase small step                                            | High   | Check vibration_rms_g and current     |
| Speed integral compensation | Speed integral time constant                            | Improve low-speed tracking                | low speed error / drift                           | Decrease carefully for faster response                         | Medium | Check hunting at stop                 |
| Feed-forward                | Position / speed feed-forward gain                      | Reduce lag during acceleration            | accel_error and position_error rise together      | Increase gradually                                             | Medium | Check overshoot on decel              |
| Torque limit                | Forward/reverse torque limit                            | Protect mechanism and reduce current trip | current_limit_pct high / jam risk                 | Lower limit for protection or raise if undersized after review | High   | Confirm mechanical capacity           |
| Current filter              | Current command filter / low-pass filter                | Reduce current ripple/noise               | current ripple and vibration noise                | Increase filtering carefully                                   | Medium | Check response delay                  |
| Notch filter                | Machine resonance suppression filter                    | Suppress resonance frequency              | resonance_amp high / FFT peak                     | Enable/tune notch around detected frequency                    | Medium | FFT before/after comparison           |
| Vibration suppression       | Vibration suppression control                           | Reduce settling vibration                 | vibration_rms_g high after move                   | Enable suppression and tune frequency                          | Medium | Measure settling time                 |
| Load inertia ratio          | Load to motor inertia ratio                             | Improve model accuracy                    | AI inertia estimate changes                       | Update estimated ratio                                         | Medium | Retune gains after change             |
| In-position range           | In-position width                                       | Avoid false complete or slow cycle        | motion_complete mismatch                          | Tighten or relax based on process tolerance                    | Low    | Vision/AOI quality check              |
| Following error limit       | Excessive error threshold                               | Early protection                          | position_error rising before alarm                | Set warning/trip limits                                        | High   | Verify no nuisance trips              |
| Soft limit                  | Positive/negative software limits                       | Prevent collision                         | near limit / overtravel risk                      | Set according to stroke                                        | High   | Slow jog validation                   |
| Brake timing                | Brake release/hold timing                               | Protect vertical Z axis                   | brake failure or slip detected                    | Adjust release/hold delay                                      | High   | Vertical load safety test             |
| Forced stop decel           | Emergency/forced stop deceleration                      | Safety stop behavior                      | E-stop or STO events                              | Set safe decel profile                                         | High   | Risk assessment and safety validation |

## 7. Fault-to-Feature 診斷矩陣

![Fault Feature Matrix](figures/fault_feature_diagnosis_matrix.png)

## 8. AI 判斷後回饋修改三菱參數

### 8.1 Following Error 過大

判斷條件：position_error_pulse P95 明顯升高，且 vibration_rms_g 未升高。  
建議：先做 auto tuning，確認 load inertia ratio，再小幅提高 position loop gain / speed loop gain。  
驗證：低速 dry run、檢查 overshoot、current_rms_a、in_position 與 AOI offset。

### 8.2 共振或高振動

判斷條件：vibration_rms_g、resonance_amp、fft_1x/2x 出現穩定峰值。  
建議：優先檢查機構鎖固、聯軸器與軸承，再啟用 notch filter 或 vibration suppression。  
驗證：比較調整前後 FFT peak、settling time、position error。

### 8.3 過熱

判斷條件：motor_temp_c 或 drive_temp_c 斜率上升，current_rms_a 同時偏高。  
建議：降低 acceleration/deceleration aggressive level、檢查負載、降低 torque limit 或 duty cycle。  
驗證：溫升曲線、current margin、cycle time 是否可接受。

### 8.4 Encoder 漂移或雜訊

判斷條件：encoder_error_count 漸進偏移或高頻抖動。  
建議：先檢查 encoder cable、接地、屏蔽、接頭與雜訊來源，再考慮 encoder filter、home offset 或 absolute position reset。  
驗證：重複回原點、長行程定位、AOI offset。

### 8.5 通訊異常

判斷條件：network_jitter_ms、packet_loss_pct、ethercat_sync_error_us、WKC error 上升。  
建議：先修網路與 PLC cycle，不要先調 servo gain。  
驗證：封包錯誤歸零、scan time 穩定後再做 servo tuning。

## 9. AI 模型使用方式

| 任務 | 模型 | 輸入 | 輸出 |
|---|---|---|---|
| Fault Classification | XGBoost / LightGBM / CatBoost | Tabular features | fault_category |
| Sequence Classification | LSTM / Transformer / Informer / PatchTST | Sliding window | fault_stage / fault_type |
| Anomaly Detection | AutoEncoder / Isolation Forest | Normal baseline | anomaly_score |
| RUL Regression | LSTM / XGBoost | degradation windows | rul_sec |
| Digital Twin | Regression / Sequence model | command + context | residual and mismatch |

## 10. HMI 畫面建議

HMI 應包含：

- AI Health Index
- Current fault category
- Fault stage
- RUL countdown
- Parameter proposal
- Risk level
- Required approval role
- Backup status
- Dry-run result
- Apply / Reject / Rollback buttons

## 11. 導入步驟

1. 先只讀資料，不寫參數。
2. 建立 baseline：正常週期、負載、溫度、振動、AOI 品質。
3. 建立模型：classification、anomaly、RUL、digital twin。
4. 導入 HMI 顯示 AI 建議。
5. 建立參數備份與版本控管。
6. 只允許工程模式下寫入參數。
7. 每次調整後強制 low speed dry run。
8. 自動比較調整前後 KPI。
9. 若 KPI 變差，自動 rollback。

## 12. 結論

AI Servo 的價值不只是預測故障，而是把資料分析結果轉成可管控的工程行動。真正可落地的架構必須包含資料串接、異常診斷、參數建議、安全審核、試跑驗證與回復機制。這樣才能把 Servo AI Dataset 轉成接近大型自動化產線可用的閉環改善系統。
