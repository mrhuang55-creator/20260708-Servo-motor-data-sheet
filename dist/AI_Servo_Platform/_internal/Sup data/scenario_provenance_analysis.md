# 40 個場景資料溯源分層與信心度校正分析報告

產出日期：2026-07-16

## 一、信心度 Lookup Bug 說明

`ai_engine.py` 中信心度計算方式：
```python
"confidence": round(scores.get(root, scores[max(scores, key=scores.get)]), 4)
```

`scores` 字典的 key 只有粗分類（`following_error`, `thermal_motor`, `thermal_drive`, `vibration`, `bearing`, `torque_ripple`, `current_load`, `network`, `digital_twin_error`, `encoder_drift`, `encoder_noise`, `encoder_signal_loss`），但 40 個場景各自的 `root`（如 `resonance`, `jam`, `rotor_unbalance`...）多數不在這個集合裡，導致 `scores.get(root, ...)` 找不到對應鍵值，`confidence` 會退化成「整個 scores 字典裡分數最高的粗分類值」，而非該場景真正的判定依據。

**實測結果：40 個場景中有 36 個（90%）受此 bug 影響**，
僅 Scenario 1（normal，無需判定）與 4、5、6（root 命名剛好對上 scores key）不受影響。

## 二、分層乘數分布統計

| 最低分層 | 乘數 | 場景數 | 佔比 | 場景 ID |
|---|---|---|---|---|
| raw | 1.00 | 1 | 2.5% | 1 |
| derived | 0.95 | 8 | 20.0% | 7, 9, 10, 11, 12, 15, 30, 37 |
| virtual_sensor | 0.70 | 3 | 7.5% | 2, 3, 34 |
| unavailable | 0.40 | 13 | 32.5% | 4, 5, 6, 8, 14, 16, 18, 19, 29, 31, 32, 36, 39 |
| fabricated_not_in_dataset | 0.30 | 15 | 37.5% | 13, 17, 20, 21, 22, 23, 24, 25, 26, 27, 28, 33, 35, 38, 40 |

> **關鍵發現**：沒有任何實際故障判定場景（Scenario 2-40）能拿到 1.0 乘數；37.5% 的場景（15 個）判定依據的最低信任層是 `fabricated_not_in_dataset`（0.3 倍），包含 Scenario 26（共振）、Scenario 28（緊急停止）等關鍵場景。

## 三、40 個場景完整明細

| ID | 場景名稱 | root_cause | Bug影響 | 判定 Tags → 分層 | 最低分層 | 乘數 |
|---|---|---|---|---|---|---|
| 1 | Pick & Place (定位到位時間優化) | `normal` | 無影響 | （無，預設健康基線） | **raw** | 1.00 |
| 2 | Press Axis (重載配合/繞組溫升估算) | `motor_over_temp` | 是 | `motor_temp_c`→virtual_sensor | **virtual_sensor** | 0.70 |
| 3 | Tray Loader (高速搬運/溫升率警告) | `drive_over_temp` | 是 | `drive_temp_c`→virtual_sensor | **virtual_sensor** | 0.70 |
| 4 | XY Gantry (長行程定位/雙軸同步與反向補償) | `encoder_drift` | 否 | `encoder_drift_pulse`→unavailable | **unavailable** | 0.40 |
| 5 | Vision Stage (微對位定位/編碼器高頻震動) | `encoder_noise` | 否 | `encoder_error_count`→unavailable | **unavailable** | 0.40 |
| 6 | Conveyor (高速往返輸送/皮帶抖動) | `encoder_signal_loss` | 否 | `encoder_error_count`→unavailable | **unavailable** | 0.40 |
| 7 | Robot Joint (高速加減速/軌跡追隨錯誤) | `position_deviation_too_large` | 是 | `following_error_abs_pulse`→derived | **derived** | 0.95 |
| 8 | Spindle (高速旋轉主軸/軸心擺動速度過高) | `over_speed` | 是 | `digital_twin_speed_residual`→unavailable | **unavailable** | 0.40 |
| 9 | Indexer (S曲線旋轉/轉換點過沖抑制) | `acceleration_overshoot` | 是 | `torque_error_nm`→derived | **derived** | 0.95 |
| 10 | Inspection (短行程幾何/減速殘留震動) | `deceleration_failure` | 是 | `following_error_abs_pulse`→derived | **derived** | 0.95 |
| 11 | Press Fit (精密壓入/峰值電流限制) | `over_current` | 是 | `current_rms_a`→derived | **derived** | 0.95 |
| 12 | Clamp (扭矩夾緊與維持/時間與扭矩和) | `torque_saturation` | 是 | `torque_error_nm`→derived | **derived** | 0.95 |
| 13 | Transfer Arm (卡檢/卡死扭矩變動率) | `jam` | 是 | `plc_estop_active`→fabricated_not_in_dataset; `torque_error_nm`→derived | **fabricated_not_in_dataset** | 0.30 |
| 14 | Rotary Table (軸承狀態/BPFO特徵幅值與震動) | `bearing_wear` | 是 | `bearing_bpfo_amp`→unavailable | **unavailable** | 0.40 |
| 15 | Linear Stage (導軌/潤滑老化摩擦力估算) | `lubrication_degradation` | 是 | `torque_error_nm`→derived | **derived** | 0.95 |
| 16 | Rotor (轉子不平衡旋轉/擺動震動位移) | `rotor_unbalance` | 是 | `vibration_rms_g`→unavailable; `fft_1x_amp`→unavailable | **unavailable** | 0.40 |
| 17 | Coupling (聯軸器偏差/角度偏差高頻共振) | `coupling_misalignment` | 是 | `vibration_rms_g`→unavailable; `frequency_response_100hz_db`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 18 | Ball Screw (滾珠絲槓/磨損導致反向間隙) | `lead_screw_wear` | 是 | `encoder_drift_pulse`→unavailable | **unavailable** | 0.40 |
| 19 | Index Table (分度盤/空程間隙多重分類) | `gear_backlash` | 是 | `encoder_drift_pulse`→unavailable | **unavailable** | 0.40 |
| 20 | Scanner (結構低頻震動/結構共振頻率) | `structural_vibration` | 是 | `vibration_rms_g`→unavailable; `resonance_frequency_hz`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 21 | Power Test (電網電源/母線電壓紋波比) | `power_grid_fluctuation` | 是 | `current_unbalance_pct`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 22 | Peak Load (加速母線欠壓/電流限制與跌落值) | `under_voltage_sag` | 是 | `current_unbalance_pct`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 23 | PLC Sync (通訊同步超時/時基抖動) | `communication_timeout` | 是 | `network_jitter_ms`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 24 | EtherCAT (數據表/網路丟包與中斷時間) | `network_packet_loss` | 是 | `ethercat_packet_loss_pct`→fabricated_not_in_dataset; `following_error_abs_pulse`→derived | **fabricated_not_in_dataset** | 0.30 |
| 25 | Precision Axis (高精密/位置高頻自激嘯叫) | `gain_instability` | 是 | `following_error_abs_pulse`→derived; `frequency_response_100hz_db`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 26 | Resonance (共振激振/機械台板主共振頻率) | `resonance` | 是 | `vibration_rms_g`→unavailable; `frequency_response_100hz_db`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 27 | Vertical Z (垂直軸防下滑/煞車釋放下滑量) | `brake_failure` | 是 | `brake_status_bool`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 28 | Prod Line (生產線急停/制動最大減速阻尼扭矩) | `emergency_stop` | 是 | `plc_estop_active`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 29 | Factory (多重故障失效/溫升與性能併發退化) | `combined_fault` | 是 | `motor_temp_c`→virtual_sensor; `vibration_rms_g`→unavailable | **unavailable** | 0.40 |
| 30 | Pred Maint (預測壽命/RUL剩餘壽命估算) | `progressive_failure` | 是 | `health_index`→derived | **derived** | 0.95 |
| 31 | Belt Slackness (皮帶鬆弛/長時間張力下滑) | `belt_slackness` | 是 | `vibration_rms_g`→unavailable; `following_error_abs_pulse`→derived | **unavailable** | 0.40 |
| 32 | Gear Tooth Breakage (減速機齒輪斷齒/嚙合局部損傷) | `gear_tooth_breakage` | 是 | `torque_error_nm`→derived; `vibration_rms_g`→unavailable; `bearing_bpfo_amp`→unavailable | **unavailable** | 0.40 |
| 33 | Guide Rail Jamming (導軌異物卡阻/局部阻力突變) | `guide_rail_jamming` | 是 | `torque_error_nm`→derived; `plc_estop_active`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 34 | Rotor Demagnetization (轉子永磁體高溫退磁) | `rotor_demagnetization` | 是 | `motor_temp_c`→virtual_sensor; `current_rms_a`→derived; `torque_error_nm`→derived | **virtual_sensor** | 0.70 |
| 35 | Phase Open Circuit / Unbalance (定子線圈不對稱/單相局部短路或開路) | `phase_open_unbalance` | 是 | `current_unbalance_pct`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 36 | External Collision Detection (外部突發碰撞/防撞安全保護) | `external_collision` | 是 | `torque_error_nm`→derived; `vibration_rms_g`→unavailable | **unavailable** | 0.40 |
| 37 | Load Inertia Mismatch (負載慣量嚴重失配/過大工件誤換) | `load_inertia_mismatch` | 是 | `following_error_abs_pulse`→derived; `torque_error_nm`→derived | **derived** | 0.95 |
| 38 | Continuous Micro-Oscillation (微幅持續抖動/伺服回路過增益自激) | `continuous_micro_oscillation` | 是 | `vibration_rms_g`→unavailable; `following_error_abs_pulse`→derived; `frequency_response_100hz_db`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |
| 39 | Encoder Pulse Drop (編碼器訊號偶發丟脈衝/光柵髒污) | `encoder_pulse_drop` | 是 | `encoder_drift_pulse`→unavailable | **unavailable** | 0.40 |
| 40 | Power Cable Intermittent Contact (馬達動力線高彈性拖鏈斷芯/接觸不良) | `power_cable_contact_degradation` | 是 | `current_rms_a`→derived; `current_unbalance_pct`→fabricated_not_in_dataset | **fabricated_not_in_dataset** | 0.30 |

## 四、待確認事項

1. **`health_index` 分層**：目前暫定為 `derived`，但 `ai_engine.py` 未見其計算公式來源，需在 `phm_pipeline.py`（未上傳）中確認是否單純由 `DV`（raw）換算而來，此項直接影響 Scenario 30 的最終信心度（0.95 vs 更低）。
2. **`digital_twin_speed_residual` / `fft_1x_amp`**：暫定為 `unavailable`，邏輯上與 `digital_twin_pos_residual` / `vibration_rms_g` 一致，建議維持此判斷。
3. **`relevant_tags` 的資料來源**：本報告採用「診斷規則中實際引用的欄位」（`DIAGNOSE_ROOT_CAUSE` 表），而非 `ai_servo_engine_v6.py` 的 `SCENARIOS_LIBRARY`，因為兩者服務不同目的（前者是故障判定依據，後者是應用場景的資料採集清單），混用會導致溯源結果失真。