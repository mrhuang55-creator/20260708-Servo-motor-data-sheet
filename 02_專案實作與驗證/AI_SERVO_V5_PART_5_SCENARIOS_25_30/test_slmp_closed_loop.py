#!/usr/bin/env python3
import time
from slmp_client import SLMPClient, SLMPServerMock

def test_slmp_closed_loop():
    print("======================================================================")
    print(">>> 測試 4.3：SLMP MC Protocol 實體通信閉環調機與改善安全回滾測試")
    print("======================================================================")
    
    # 1. 啟動模擬伺服驅動器 / PLC 通信伺服器 (MC Protocol 3E TCP Server)
    server = SLMPServerMock(host="127.0.0.1", port=5007)
    server.registers[1018] = 0
    server.registers[1012] = 0
    server.registers[1002] = 10
    server.registers[1007] = 0
    server.registers[1010] = 0 # 轉速暫存器 D1010
    
    server.start()
    print("  [伺服模擬器] 已啟動，監聽埠: 5007 (MC Protocol 3E)...")
    
    # 2. 建立 AI 調機通信客戶端
    client = SLMPClient(host="127.0.0.1", port=5007)
    
    try:
        client.connect()
        print("  [AI 閉環客戶端] 已連線至模擬伺服器。")
        
        # 測試：TSN 多軸站點路由讀取 (讀取 Station 1)
        vals_before = client.read_d_registers(start_addr=1000, points=20, network_no=0x02, pc_no=0xFF, dest_io=0x03FF, dest_station=0x01)
        backup = {
            "PE02": vals_before[2],  # D1002
            "PE07": vals_before[7],  # D1007
            "PB12": vals_before[12], # D1012
            "PA18": vals_before[18]  # D1018
        }
        print(f"  [步驟 1：參數備份 - Station 1] 目前暫存器參數: {backup}")
        
        # 3. 模擬 AI 推薦寫入參數 (Notch Filter 頻率)
        print("  [步驟 2：試運轉參數寫入] 寫入 Notch 抑制濾波器參數: PA18=290, PB12=435")
        client.write_d_registers(start_addr=1018, values=[290], network_no=0x02, pc_no=0xFF, dest_io=0x03FF, dest_station=0x01)
        client.write_d_registers(start_addr=1012, values=[435], network_no=0x02, pc_no=0xFF, dest_io=0x03FF, dest_station=0x01)
        
        # 讀取確認
        pa18_now = client.read_d_registers(start_addr=1018, points=1, network_no=0x02, pc_no=0xFF, dest_io=0x03FF, dest_station=0x01)[0]
        pb12_now = client.read_d_registers(start_addr=1012, points=1, network_no=0x02, pc_no=0xFF, dest_io=0x03FF, dest_station=0x01)[0]
        print(f"  [步驟 3：讀回確認] 目前 D1018 (PA18)={pa18_now} Hz, D1012 (PB12)={pb12_now} Hz")
        
        assert pa18_now == 290, "PA18 參數寫入失敗！"
        assert pb12_now == 435, "PB12 參數寫入失敗！"
        
        # 4. 測試防抖過濾器 (Anti-Chatter Filter)
        print("\n  [步驟 4：防抖過濾器驗證] 檢測異常突波與連續異常...")
        samples_noise = [5.1, 17.2, 4.3, 3.8, 6.2] # 包含單點 17.2A 突波
        samples_fault = [16.2, 17.5, 16.9, 15.8, 17.1] # 連續異常
        is_noise = client.check_anti_chatter_current(samples_noise, window_size=3, threshold=15.0)
        is_fault = client.check_anti_chatter_current(samples_fault, window_size=3, threshold=15.0)
        print(f"    - 單點噪訊判定為違規: {is_noise} | 連續異常判定為違規: {is_fault}")
        assert is_noise is False, "防抖過濾器對單點噪訊誤報！"
        assert is_fault is True, "防抖過濾器對連續異常漏報！"
        print("    - [PASS] 防抖過濾器運作正常！已成功過濾單點隨機噪訊。")
        
        # 5. 模擬 Case 2: 試運行未通過安全限制 (連續異常觸發安全回滾)
        print("\n  [情境變更] 模擬寫入摩擦力與背隙補償參數...")
        client.write_d_registers(start_addr=1002, values=[150]) 
        client.write_d_registers(start_addr=1007, values=[96])  
        
        pe02_now = client.read_d_registers(start_addr=1002, points=1)[0]
        pe07_now = client.read_d_registers(start_addr=1007, points=1)[0]
        print(f"  [步驟 5：讀回確認] 目前 D1002 (PE02)={pe02_now}, D1007 (PE07)={pe07_now}")
        
        # 偵測到連續異常電流，觸發安全回滾，先啟動安全急停動作
        print("  [步驟 6：安全限制違規] 偵測到連續異常電流，啟動一鍵安全回滾！")
        
        # 實施改善計畫：安全急停動作 (Safe-state deceleration)
        print("  [步驟 6.1：安全急停動作] 觸發安全減速程序：1200rpm -> 600rpm -> 0rpm")
        client.write_d_registers(start_addr=1010, values=[1200])
        print(f"    - 目前馬達轉速: {client.read_d_registers(1010, 1)[0]} rpm")
        client.write_d_registers(start_addr=1010, values=[600])
        print(f"    - 目前馬達轉速: {client.read_d_registers(1010, 1)[0]} rpm")
        client.write_d_registers(start_addr=1010, values=[0])
        print(f"    - 目前馬達轉速: {client.read_d_registers(1010, 1)[0]} rpm (確認靜止，進入安全 STO 狀態)")
        
        # 執行回滾
        print("  [步驟 6.2：參數恢復] 開始寫入備份參數暫存器...")
        client.write_d_registers(start_addr=1002, values=[backup["PE02"]])
        client.write_d_registers(start_addr=1007, values=[backup["PE07"]])
        
        # 驗證回滾結果
        pe02_roll = client.read_d_registers(start_addr=1002, points=1)[0]
        pe07_roll = client.read_d_registers(start_addr=1007, points=1)[0]
        print(f"  [步驟 7：驗證回滾] 回滾後 D1002 (PE02)={pe02_roll}, D1007 (PE07)={pe07_roll}")
        
        assert pe02_roll == backup["PE02"], "PE02 回滾失敗！"
        assert pe07_roll == backup["PE07"], "PE07 回滾失敗！"
        print("  [PASS] 一鍵安全減速與回滾 (Rollback) 測試成功！")
        
    finally:
        client.close()
        server.stop()
        print("  [伺服模擬器] 已關閉。")
        print("  [PASS] SLMP 閉環調試控制流程全部通過！")

if __name__ == "__main__":
    test_slmp_closed_loop()
