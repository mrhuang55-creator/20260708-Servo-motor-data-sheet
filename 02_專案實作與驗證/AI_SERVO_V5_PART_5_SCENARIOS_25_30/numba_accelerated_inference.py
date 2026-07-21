#!/usr/bin/env python3
"""
numba_accelerated_inference.py
NumPy MLP vs Numba JIT 加速推理時滯對比測試
目的：量化 Numba @njit 裝飾器對前向推理的加速效果
"""
import numpy as np
import time

def sigmoid_np(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def softmax_np(x):
    x_shifted = x - np.max(x)
    e_x = np.exp(np.clip(x_shifted, -500, 500))
    return e_x / (np.sum(e_x) + 1e-12)

# ============================================================
# 1. 純 NumPy 推理核心（基準）
# ============================================================
def mlp_inference_numpy(X, W1, b1, W2, b2, W3, b3):
    """純 NumPy 版本前向傳播"""
    z1 = np.dot(X, W1) + b1
    a1 = np.maximum(0, z1)
    z2 = np.dot(a1, W2) + b2
    a2 = np.maximum(0, z2)
    z3 = np.dot(a2, W3) + b3
    # Stabilized softmax
    z3_shifted = z3 - np.max(z3, axis=-1, keepdims=True)
    e_z3 = np.exp(np.clip(z3_shifted, -500, 500))
    return e_z3 / (np.sum(e_z3, axis=-1, keepdims=True) + 1e-12)

# ============================================================
# 2. 嘗試使用 Numba JIT 加速
# ============================================================
try:
    from numba import njit

    @njit(fastmath=True, cache=True)
    def mlp_inference_numba(X, W1, b1, W2, b2, W3, b3):
        """Numba JIT 版本前向傳播（活化 AVX2/AVX512 SIMD 指令集）"""
        # Layer 1: ReLU
        z1 = X @ W1 + b1
        a1 = z1.copy()
        for i in range(len(a1)):
            if a1[i] < 0.0:
                a1[i] = 0.0
        # Layer 2: ReLU
        z2 = a1 @ W2 + b2
        a2 = z2.copy()
        for i in range(len(a2)):
            if a2[i] < 0.0:
                a2[i] = 0.0
        # Layer 3: Linear
        z3 = a2 @ W3 + b3
        # Softmax
        max_z3 = z3[0]
        for v in z3:
            if v > max_z3:
                max_z3 = v
        e_z3 = z3.copy()
        s = 0.0
        for i in range(len(z3)):
            e_z3[i] = np.exp(min(z3[i] - max_z3, 500.0))
            s += e_z3[i]
        for i in range(len(z3)):
            e_z3[i] /= (s + 1e-12)
        return e_z3

    NUMBA_AVAILABLE = True
    print("  [Numba] Numba 已安裝，JIT 加速推理功能啟用。")

except ImportError:
    NUMBA_AVAILABLE = False
    print("  [Numba] Numba 未安裝，僅顯示 NumPy 基準結果。")
    print("  → 安裝指令：pip install numba")

# ============================================================
# 3. 對比測試主程式
# ============================================================
def run_inference_benchmark():
    print("\n" + "=" * 68)
    print(">>> NumPy MLP 推理時滯對比測試 (NumPy vs Numba JIT)")
    print("=" * 68)

    np.random.seed(42)
    INPUT_DIM, H1, H2, OUTPUT_DIM = 4, 64, 32, 12
    W1 = np.random.randn(INPUT_DIM, H1).astype(np.float64) * np.sqrt(2.0 / INPUT_DIM)
    b1 = np.zeros((1, H1))
    W2 = np.random.randn(H1, H2).astype(np.float64) * np.sqrt(2.0 / H1)
    b2 = np.zeros((1, H2))
    W3 = np.random.randn(H2, OUTPUT_DIM).astype(np.float64) * np.sqrt(2.0 / H2)
    b3 = np.zeros((1, OUTPUT_DIM))

    X_single = np.random.randn(1, INPUT_DIM)

    N_WARMUP = 100
    N_BENCHMARK = 100_000
    numba_latency_us = 0.0

    # ------- NumPy 測試 -------
    for _ in range(N_WARMUP):
        mlp_inference_numpy(X_single, W1, b1, W2, b2, W3, b3)

    t0 = time.perf_counter()
    for _ in range(N_BENCHMARK):
        mlp_inference_numpy(X_single, W1, b1, W2, b2, W3, b3)
    t1 = time.perf_counter()
    numpy_latency_us = (t1 - t0) / N_BENCHMARK * 1e6
    print(f"\n  [NumPy 基準] 單次推理平均延遲：{numpy_latency_us:.4f} us ({numpy_latency_us/1000:.6f} ms)")

    # ------- Numba JIT 測試 -------
    if NUMBA_AVAILABLE:
        # 單筆輸入（1D）
        X_1d = X_single.flatten()
        W1_f = W1.astype(np.float64)
        W2_f = W2.astype(np.float64)
        W3_f = W3.astype(np.float64)
        b1_1d = b1.flatten()
        b2_1d = b2.flatten()
        b3_1d = b3.flatten()

        print("  [Numba] 首次編譯（JIT 預熱中）...")
        for _ in range(N_WARMUP):
            mlp_inference_numba(X_1d, W1_f, b1_1d, W2_f, b2_1d, W3_f, b3_1d)

        t0 = time.perf_counter()
        for _ in range(N_BENCHMARK):
            mlp_inference_numba(X_1d, W1_f, b1_1d, W2_f, b2_1d, W3_f, b3_1d)
        t1 = time.perf_counter()
        numba_latency_us = (t1 - t0) / N_BENCHMARK * 1e6
        speedup = numpy_latency_us / numba_latency_us if numba_latency_us > 0 else float('inf')
        print(f"  [Numba JIT] 單次推理平均延遲：{numba_latency_us:.4f} us ({numba_latency_us/1000:.6f} ms)")
        print(f"  [加速倍率] Numba 比 NumPy 快了 {speedup:.1f}x")

    # ------- 結果摘要 -------
    print("\n" + "=" * 68)
    print("  推理延遲對比摘要")
    print("=" * 68)
    print(f"  | 方案           | 延遲 (us)            | 適配 1ms 控制週期 |")
    print(f"  | NumPy 手刻     | {numpy_latency_us:>8.4f} us         | {'[OK]' if numpy_latency_us < 100 else '[WARN]':<6} |")
    if NUMBA_AVAILABLE:
        print(f"  | Numba JIT 加速 | {numba_latency_us:>8.4f} us         | {'[OK]' if numba_latency_us < 100 else '[WARN]':<6} |")
    print("=" * 68)
    print("  [PASS] 推理時滯對比測試完成！")

if __name__ == "__main__":
    run_inference_benchmark()
