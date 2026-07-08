# 伺服系統故障診斷與健康管理特徵分析與標籤映射規格書
**工業 AI 系統架構規範文件**

---

## 1. 121 個 Servo Tags 完整映射架構

在 1000Hz 高頻採樣率下，伺服感測數據與控制訊號被分類為五大範疇，共 121 個 Tags。下表定義其分類架構，並重點標註核心分析 Tags。

### 1.1 五大資料範疇定義
1. **運動控制與位置特徵 (Motion & Position, 25 Tags)**：追蹤指令與實際運動的偏差。
2. **電氣與電流特徵 (Electrical & Current, 24 Tags)**：分析電機驅動電磁狀態與三相電流對稱性。
3. **機械動力學與振動特徵 (Dynamics & Vibration, 24 Tags)**：頻率分析與機構物理阻尼/剛性評估。
4. **網路與 PLC 通訊特徵 (Communication & Network, 24 Tags)**：判定即時控制匯流排（如 EtherCAT）傳輸品質。
5. **系統邏輯與連鎖安全 (Logical & Interlocks, 24 Tags)**：硬體與軟體安全狀態的布林狀態特徵。

### 1.2 四大核心 Tag 詳細定義

| 核心分析指標 | 標準 Tag 代稱 | 採樣率 | 物理單位 | 作用與診斷價值 |
| :--- | :--- | :--- | :--- | :--- |
| **位置殘差 (Position Residuals)** | `digital_twin_pos_residual` | 1000Hz | pulse (脈衝) | 數位雙生模型預估位置與實際位置之差，用於扣除加減速動態響應後的「機械純殘差」，能極敏感地捕捉微小機構磨損或異常卡阻。 |
| **電流不平衡率 (Current Unbalance)** | `current_unbalance_pct` | 1000Hz | % | 依據三相電流的負序分量與正序分量比例計算。當馬達繞組異常、接線鬆脫或驅動器 IGBT 老化時，此值會顯著升高。 |
| **振動頻率響應 (Frequency Response)** | `frequency_response_100hz_db` | 1000Hz (FFT) | dB | 振動感測器 FFT 後在 100Hz 以上頻域的振幅。用於偵測機械剛性降低引起的共振或伺服增益過高造成的迴路震盪。 |
| **通訊封包流失率 (EtherCAT Packet Loss)** | `ethercat_packet_loss_pct` | 100Hz | % | 滾動計算每一秒內丟失或受損的 EtherCAT 封包比例。若大於 0% 則表示有通訊雜訊或線路受損。 |

*(其餘 117 個 Tags 列表包含：馬達速度、轉矩指令、母線電壓、繞組溫度、編碼器單圈位置、編碼器多圈位置、光學尺回授、三相電壓、諧波畸變率(THD)、負載慣量比、軸承溫度、BPFO/BPFI振幅、PLC掃描時間、指令抖動率、同步誤差、煞車動作延遲、STO狀態、急停極限訊號等。)*

---

## 2. 故障診斷矩陣 (Diagnosis Matrix - Scenarios 01-06 & 25-30)

以下針對健康基準、基礎故障與進階故障情境制定完整診斷矩陣，定義| **Scenario 07** | **聯軸器對中不良**<br>(Coupling Misalignment) | `vibration_rms_g`<br>`fft_1x_amp` | 振動有效值增加且在特定旋轉頻率（1x 諧波振幅）顯著升高。 | 速度增益、強韌濾波器、機械對中檢修 | 降低 vibration_rms_g，消除特定諧波峰值 |
| **Scenario 08** | **皮帶張力鬆動**<br>(Belt Slack) | `following_error_abs_pulse`<br>`vibration_rms_g` | 加速期間追隨誤差增大，且伴隨低頻晃動振幅上升。 | 位置環增益、加減速時間常數、指令平滑濾波 | 減少加減速定位晃動，穩定位置環 |
| **Scenario 09** | **減速機背隙過大**<br>(Gearbox Backlash) | `digital_twin_pos_residual`<br>`encoder_drift_pulse` | 反向運動時位置殘差滯後，漂移特徵有穩態偏差。 | 遺失運動補償 (Lost Motion)、反向間隙補償 (PE07) | 降低雙向定位滯後誤差，補償背隙 |
| **Scenario 10** | **絲杠磨損/摩擦力大**<br>(Ball Screw Wear) | `torque_error_nm`<br>`current_rms_a`<br>`motor_temp_c` | 雙向運動轉矩指令誤差均升高，馬達溫度緩緩上升且工作電流增加。 | 摩擦力補償 (PE02)、轉矩限制值 | 降低雙向定速轉矩誤差，限制工作電流 |
| **Scenario 11** | **輸出缺相/電流不平衡**<br>(Phase Loss) | `current_unbalance_pct`<br>`motor_temp_c` | 三相電流不平衡率高於 3.0%，伴隨繞組溫度急升。 | 電流限制、轉矩限制值 (PA11)、三相接線檢修 | 降低電流不平衡率，控制馬達溫升斜率 |
| **Scenario 12** | **母線過電壓**<br>(Bus Overvoltage) | `drive_temp_c`<br>`torque_error_nm` | 減速階段驅動器溫度急升，伴隨大負值轉矩指令，引發回生過電壓警告。 | 減速時間常數 (PC24)、母線電容吸收檢修 | 消除回生過載警告，降低減速溫升 |
| **Scenario 13** | **母線欠壓**<br>(Bus Undervoltage) | `following_error_abs_pulse`<br>`current_rms_a` | 加速瞬間電流不足且追隨誤差突增，主迴路直流母線電壓下探。 | 加速時間常數 (PC24)、電源線路檢修 | 避免加速追隨誤差突增，平緩電網抽載 |
| **Scenario 14** | **機械過載卡阻**<br>(Mechanical Jam) | `torque_error_nm`<br>`following_error_abs_pulse` | 轉矩誤差極高且追隨誤差持續累積，馬達運作被限制在扭矩上限。 | 轉矩限制值 (PA11)、強制停止減速常數 | 保護機械免受過載衝擊，觸發安全急停 |
| **Scenario 15** | **冷卻風扇故障**<br>(Fan Failure) | `drive_temp_c`<br>`current_rms_a` | 驅動器溫度高於 85°C，但工作電流與負載完全在正常區間。 | 降級工作負載率、冷卻風扇更換 | 降低驅動器最高溫度，避免高溫警報 |
| **Scenario 16** | **接地雜訊干擾**<br>(Ground Noise) | `encoder_error_count`<br>`following_error_abs_pulse` | 編碼器錯誤計數大於 50，且實際追隨誤差伴隨高頻無規則毛刺。 | 電流濾波時間常數 (PB18)、屏蔽與接地檢修 | 平滑編碼器反饋，濾除接地毛刺 |
| **Scenario 17** | **極限開關觸發**<br>(Limit Switch Active) | `plc_estop_active`<br>`brake_status_bool` | 正/負硬體極限開關動作，速度指令降至 0。 | 強制停止減速時間 (PC24)、電磁煞車釋放時序 | 立刻啟動安全煞車鎖死，防超行程碰撞 |
| **Scenario 18** | **加減速過大**<br>(Accel Aggressive) | `current_rms_a`<br>`following_error_abs_pulse` | 加減速暫態區間，電流與追隨誤差同步出現極高脈衝峰值。 | 加減速時間常數 (PC24)、指令平滑濾波器 | 平滑加減速峰值電流，改善過載裕度 |
| **Scenario 19** | **動態制動失效**<br>(Dynamic Brake Fail) | `following_error_abs_pulse`<br>`vibration_rms_g` | 減速停止時滑行時間大於設定常數，位置殘差拖尾嚴重。 | 電磁煞車動作延遲 (PC16)、制動電阻檢查 | 縮短減速停止距離，消除停止位移拖尾 |
| **Scenario 20** | **指令抖動**<br>(Command Jitter) | `network_jitter_ms`<br>`following_error_abs_pulse` | PLC 運算指令抖動大，`network_jitter_ms` 升高，馬達速度無規則波動。 | 指令平滑濾波 (PB18)、PLC 控制週期優化 | 消除速度抖動，平滑運動軌跡 |
| **Scenario 21** | **負載慣量不匹配**<br>(Inertia Mismatch) | `following_error_abs_pulse`<br>`vibration_rms_g` | 定位穩定時間（Settling Time）過長，超調大，但無高頻震盪。 | 負載慣量比更新 (PA09/PB05)、增益重調 | 縮短 Settling time，減少階躍超調 |
| **Scenario 22** | **軸承磨損**<br>(Bearing Wear) | `bearing_bpfo_amp`<br>`bearing_bpfi_amp`<br>`health_index` | 軸承損傷特徵頻譜 BPFO/BPFI 緩慢爬升，伴隨高頻軸承溫度微升。 | 摩擦力補償 (PE02)、預防性維護計畫設定 | 預防意外停機，優化健康指標 |
| **Scenario 23** | **通訊控制喪失 / 丟包異常**<br>(Communication Loss of Control) | `ethercat_packet_loss_pct`<br>`following_error_abs_pulse` | 網路丟包率高於 2.0%，伴隨伺服跟隨誤差增大，控制性能下降。 | 優先修正 PLC 控制週期與 TSN 網路，不要先調伺服增益。 | 封包錯誤歸零，穩定跟隨誤差。 |
| **Scenario 24** | **網路同步超時**<br>(Sync Timeout) | `ethercat_sync_error_us`<br>`network_jitter_ms` | 同步誤差大於 30us，抖動高，但網路無封包丟失。 | PLC 運動指令週期、TSN同步參數優化 | 降低網路同步誤差，消除假控制失控告警 |
| **Scenario 25** | **伺服增益不穩定**<br>(Servo Gain Instability) | `following_error_abs_pulse`<br>`frequency_response_100hz_db`<br>`current_rms_a` | 速度或位置環運作時，100Hz 以上高頻出現持續抖動，且電流有效值非正常攀升。 | 速度增益 (Speed Loop Gain)、強韌濾波器 (Robust Filter)、速度積分時間常數 | 縮短 Settling time、消除高頻電流抖動 |
| **Scenario 26** | **機械共振**<br>(Resonance) | `vibration_rms_g`<br>`frequency_response_100hz_db`<br>`torque_error_nm` | 振動在特定高頻頻譜（如 120Hz, 300Hz）出現窄頻極高振幅峰值，轉矩殘差呈正弦波動。 | 機械共振抑制濾波器 (Notch Filter)、共振抑制頻率/寬度/深度 | 降低 vibration_rms_g、消除特定頻譜振幅峰值 |
| **Scenario 27** | **煞車失效**<br>(Brake Failure) | `digital_twin_pos_residual`<br>`torque_error_nm`<br>`brake_status_bool` | 煞車指令下達時，位置殘差（滑落）持續增加，且轉矩表現異常（垂直 Z 軸重力下滑）。 | 電磁煞車輸出延遲時間 (Brake Timing)、保持轉矩限制 (Hold Torque) | 垂直軸下滑量降為 0、煞車防滑落補償效能提升 |
| **Scenario 28** | **緊急停止**<br>(Emergency Stop) | `plc_estop_active`<br>`following_error_abs_pulse`<br>`torque_limit_pct` | 安全迴路或急停觸發，指令速度陡降至 0，引發大電流限制及極限位置追隨誤差。 | 強制停止減速時間常數 (Forced Stop Decel)、急停扭矩限制值 | 縮短急停停止時間與滑行距離、保護機械結構免受過大衝擊 |
| **Scenario 29** | **複合故障**<br>(Combined Fault) | `ethercat_packet_loss_pct`<br>`ethercat_sync_error_us`<br>`motor_temp_c`<br>`vibration_rms_g` | 多重異常同時發生（網路封包丟失 + 溫度上升 + 機械振動增加）。需利用互相關判定通訊與負載關聯性。 | 負載慣量比 (Inertia)、CC-Link TSN/EtherCAT 參數、指令平滑/濾波 (Command Smoothing) | 降低馬達溫度上升斜率、消除通訊引起的轉矩漣波 |
| **Scenario 30** | **漸進式失效與停機**<br>(Progressive Failure + Shutdown) | `health_index`<br>`rul_sec`<br>`bearing_bpfo_amp`<br>`bearing_bpfi_amp` | 狀態指標（如軸承外圈損傷振幅）呈時間序列趨勢性退化，健康度逐步降至 Trip 閾值。 | 機械診斷警告極限設定、速度/加速度限制常數、預防性維護警報閾值設定 | 健康指標均值 > 80、降低非預期停機機率 (Zero Downtime) |�大於 50，且實際追隨誤差伴隨高頻抖動。 | 電流濾波器 (Current Filter)、指令陷波濾波器、指令平滑濾波 | 過濾編碼器高頻回授雜訊，穩定速度環 |
| **Scenario 06** | **編碼器訊號遺失**<br>(Encoder Signal Loss) | `encoder_error_count`<br>`health_index` | 編碼器通訊完全中斷，單秒錯誤計數大於 1000，且追隨誤差急劇增加。 | 強制停止減速時間常數、煞車釋放/保持延遲時間 | 觸發急停並立刻鎖定煞車，防止重力下滑 |
| **Scenario 25** | **伺服增益不穩定**<br>(Servo Gain Instability) | `following_error_abs_pulse`<br>`frequency_response_100hz_db`<br>`current_rms_a` | 速度或位置環運作時，100Hz 以上高頻出現持續抖動，且電流有效值非正常攀升。 | 速度增益 (Speed Loop Gain)、強韌濾波器 (Robust Filter)、速度積分時間常數 | 縮短 Settling time、消除高頻電流抖動 |
| **Scenario 26** | **機械共振**<br>(Resonance) | `vibration_rms_g`<br>`frequency_response_100hz_db`<br>`torque_error_nm` | 振動在特定高頻頻譜（如 120Hz, 300Hz）出現窄頻極高振幅峰值，轉矩殘差呈正弦波動。 | 機械共振抑制濾波器 (Notch Filter)、共振抑制頻率/寬度/深度 | 降低 vibration_rms_g、消除特定頻譜振幅峰值 |
| **Scenario 27** | **煞車失效**<br>(Brake Failure) | `digital_twin_pos_residual`<br>`torque_error_nm`<br>`brake_status_bool` | 煞車指令下達時，位置殘差（滑落）持續增加，且轉矩表現異常（垂直 Z 軸重力下滑）。 | 電磁煞車輸出延遲時間 (Brake Timing)、保持轉矩限制 (Hold Torque) | 垂直軸下滑量降為 0、煞車防滑落補償效能提升 |
| **Scenario 28** | **緊急停止**<br>(Emergency Stop) | `plc_estop_active`<br>`following_error_abs_pulse`<br>`torque_limit_pct` | 安全迴路或急停觸發，指令速度陡降至 0，引發大電流限制及極限位置追隨誤差。 | 強制停止減速時間常數 (Forced Stop Decel)、急停扭矩限制值 | 縮短急停停止時間與滑行距離、保護機械結構免受過大衝擊 |
| **Scenario 29** | **複合故障**<br>(Combined Fault) | `ethercat_packet_loss_pct`<br>`ethercat_sync_error_us`<br>`motor_temp_c`<br>`vibration_rms_g` | 多重異常同時發生（網路封包丟失 + 溫度上升 + 機械振動增加）。需利用互相關判定通訊與負載關聯性。 | 負載慣量比 (Inertia)、CC-Link TSN/EtherCAT 參數、指令平滑/濾波 (Command Smoothing) | 降低馬達溫度上升斜率、消除通訊引起的轉矩漣波 |
| **Scenario 30** | **漸進式失效與停機**<br>(Progressive Failure + Shutdown) | `health_index`<br>`rul_sec`<br>`bearing_bpfo_amp`<br>`bearing_bpfi_amp` | 狀態指標（如軸承外圈損傷振幅）呈時間序列趨勢性退化，健康度逐步降至 Trip 閾值。 | 機械診斷警告極限設定、速度/加速度限制常數、預防性維護警報閾值設定 | 健康指標均值 > 80、降低非預期停機機率 (Zero Downtime) |

---

## 3. 進階診斷邏輯與數學公式

為了在高頻採樣數據中精準判定各故障情境並過濾通訊干擾，系統採用以下診斷演算法：

### 3.1 溫升與控制降級邏輯 (Scenario 02 & 03)
為防止馬達及驅動器過熱損壞，系統建立溫度梯度判定公式，當達到閾值時觸發系統降級控制：
- **馬達超溫判定**：當繞組溫度符合 $T_{\text{motor}} > 90^\circ\text{C}$ 時判定為超溫；若升溫斜率 $\frac{dT_{\text{motor}}}{dt} > 0.5^\circ\text{C/sec}$ 且電流高於額定電流 $1.2$ 倍，則觸發預警保護。
- **降級動作**：優化器會限制馬達峰值轉矩，並調整加速度時間常數。

### 3.2 編碼器位置與訊號狀態診斷 (Scenario 04-06)
- **編碼器漂移 (Encoder Drift)**：監控實際光學反饋位置 $P_{\text{act}}$ 與數位雙生參考位置 $P_{\text{ref}}$ 的穩態偏差：
  $$e_{\text{drift}} = \text{steady\_state}(|P_{\text{act}} - P_{\text{ref}}|) > 100 \text{ pulses}$$
- **編碼器雜訊 (Encoder Noise)**：高頻計數器錯誤。當 $E_{\text{count}} > 50$ 且轉矩指令高頻紋波率 $> 15\%$ 時觸發。
- **編碼器訊號遺失 (Encoder Signal Loss)**：嚴重通訊故障。當 $E_{\text{count}} > 1000$ 且位置回授突變為 0 或追隨誤差超過安全限制時觸發，系統強制實施動態制動與煞車緊鎖。

### 3.3 頻率域特徵分析 (Scenario 25-26)
在 1000Hz 採樣率下，針對 >100Hz 的高頻諧波，使用滑動窗口進行 FFT 轉換，並計算特定頻段的**顯著峰值突出度 (Peak Prominence)** $P(f)$：
$$P(f) = A(f) - \mu_{\text{local}}(f)$$
其中：
- $A(f)$ 是頻率 $f$ 處的振幅（以 dB 表示）。
- $\mu_{\text{local}}(f)$ 是該頻率兩側鄰近頻段的平均背景雜訊振幅。

**觸發判定邏輯：**
- 若存在任一頻率 $f > 100\text{ Hz}$ 使得 $P(f) > 12\text{ dB}$：
  - 若轉矩指令同步發生該頻率的抖動，則判定為 **Scenario 25 (增益不穩定)**。
  - 若主要是加速度規振動回授顯著，則判定為 **Scenario 26 (機械共振)**。

### 3.4 滾動時間視窗狀態轉變邏輯 (Scenario 30)
漸進式失效是一個時間演進過程，定義長度為 $W$ 的滾動時間視窗，計算均值與趨勢：
$$H_w(t) = \frac{1}{W} \sum_{i=0}^{W-1} \text{health\_index}(t - i)$$
狀態轉變狀態機 (State Machine) 定義如下：
1. **`normal` (正常狀態)**：$H_w(t) > 80$
2. **`early_degradation` (早期衰退)**：$50 < H_w(t) \le 80$ 且健康度斜率小於 0。
3. **`severe_warning` (嚴重告警)**：$20 < H_w(t) \le 50$ 且剩餘壽命預估 `rul_sec` 呈遞減。
4. **`trip` (停機保護)**：$H_w(t) \le 20$，強制進入安全停機狀態。

### 3.5 邏輯斷言：排除假通訊雜訊 (False Alarm Mitigation)
為了確保模型能準確區分「真機械故障」與「假通訊雜訊」，我們建立如下**邏輯斷言 (Assertion Rule)**：
$$\text{Assert: } \text{if } (ethercat\_packet\_loss\_pct > 2.0\%) \text{ and } (following\_error\_abs\_pulse > 100)$$
$$\Longrightarrow \text{Prioritize: } \text{Diagnosis} = \text{"Communication Loss" (通訊異常導致失控)}$$

---

## 4. 特徵權重建議 (Feature Weighting Matrix)

以下提供針對 Scenarios 01-06 以及 Scenarios 25-30 的特徵權重建議（0.0 至 1.0），作為模型訓練時的調參參考：

| 欄位 / 特徵名稱 | S01 | S02 | S03 | S04 | S05 | S06 | S25 | S26 | S27 | S28 | S29 | S30 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ethercat_packet_loss_pct` | 0.05 | 0.05 | 0.05 | 0.05 | 0.10 | 0.10 | 0.10 | 0.05 | 0.05 | 0.20 | **0.85** | 0.10 |
| `plc_scan_time_ms_anomaly` | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.05 | 0.15 | 0.05 | 0.05 | 0.30 | **0.80** | 0.05 |
| `digital_twin_pos_residual`| 0.10 | 0.10 | 0.10 | **0.90** | 0.40 | 0.50 | **0.70** | 0.50 | **0.90** | 0.60 | 0.60 | 0.55 |
| `current_unbalance_pct` | 0.10 | 0.40 | 0.40 | 0.20 | 0.30 | 0.30 | 0.60 | 0.30 | 0.20 | 0.40 | 0.65 | 0.50 |
| `frequency_response_100hz_db` | 0.05 | 0.05 | 0.05 | 0.10 | 0.40 | 0.10 | **0.90** | **0.95** | 0.05 | 0.10 | 0.50 | 0.40 |
| `vibration_rms_g` | 0.05 | 0.10 | 0.10 | 0.15 | 0.30 | 0.20 | 0.60 | **0.90** | 0.10 | 0.20 | 0.70 | 0.65 |
| `torque_error_nm` | 0.10 | 0.50 | 0.40 | 0.30 | 0.40 | 0.40 | 0.75 | 0.70 | **0.80** | 0.60 | **0.80** | 0.45 |
| `health_index` | 0.95 | 0.70 | 0.70 | 0.60 | 0.60 | **0.80** | 0.30 | 0.30 | 0.50 | 0.10 | 0.70 | **0.95** |
| `motor_temp_c` | 0.20 | **0.95** | 0.30 | 0.05 | 0.05 | 0.05 | 0.10 | 0.05 | 0.05 | 0.15 | **0.75** | 0.20 |
| `drive_temp_c` | 0.15 | 0.30 | **0.95** | 0.05 | 0.05 | 0.05 | 0.10 | 0.05 | 0.05 | 0.15 | 0.65 | 0.15 |
| `encoder_drift_pulse` | 0.05 | 0.05 | 0.05 | **0.98** | 0.10 | 0.10 | 0.05 | 0.05 | 0.10 | 0.05 | 0.05 | 0.10 |
| `encoder_error_count` | 0.05 | 0.05 | 0.05 | 0.10 | **0.95** | **0.99** | 0.05 | 0.05 | 0.05 | 0.05 | 0.10 | 0.05 |
| `plc_estop_active` | 0.00 | 0.05 | 0.05 | 0.00 | 0.00 | 0.10 | 0.00 | 0.00 | 0.10 | **0.99** | 0.40 | 0.05 |
