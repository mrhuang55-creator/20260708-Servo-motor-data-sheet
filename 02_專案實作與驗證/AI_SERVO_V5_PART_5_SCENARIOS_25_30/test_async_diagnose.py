#!/usr/bin/env python3
import asyncio
import pandas as pd
from ai_engine import async_diagnose_loop

async def test_async_diagnose():
    print("======================================================================")
    print(">>> 測試 1.4：AsyncIO 實時事件驅動流式診斷管道測試")
    print("======================================================================")
    
    # 建立事件佇列
    queue = asyncio.Queue()
    
    # 建立回呼收集器
    results = []
    def callback(res):
        results.append(res)
        print(f"  [Async Callback] 診斷出的場景 ID: {res['advanced_diagnostics']['scenario_id']} | 根因: {res['root_cause']}")
        
    # 啟動非同步診斷協程
    task = asyncio.create_task(async_diagnose_loop(queue, callback=callback))
    await asyncio.sleep(0.1) # 讓任務啟動
    
    # 模擬實時串流寫入事件 (例如機械共振事件)
    event_data = {
        "vibration_rms_g": 0.45,
        "following_error_abs_pulse": 25.0,
        "torque_error_nm": 1.2,
        "health_index": 62.0,
        "resonance_frequency_hz": 290.0,
        "motor_temp_c": 55.0
    }
    
    print("  [串流寫入] 寫入一組實時共振特徵到事件佇列...")
    await queue.put(event_data)
    
    # 等待處理完成
    await queue.join()
    
    # 停止協程
    await queue.put(None)
    await task
    
    assert len(results) == 1, "未收到診斷回呼結果！"
    assert results[0]['advanced_diagnostics']['scenario_id'] == 26, "共振場景診斷錯誤！"
    print("  [PASS] AsyncIO 實時事件驅動診斷測試成功！")

if __name__ == "__main__":
    asyncio.run(test_async_diagnose())
