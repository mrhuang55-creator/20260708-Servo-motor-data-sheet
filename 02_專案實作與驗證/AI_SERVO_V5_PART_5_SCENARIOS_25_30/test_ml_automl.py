#!/usr/bin/env python3
import numpy as np
from ml_automl_engine import MLCompetitionPlatform, UnsupervisedClustering, GeneticAlgorithmTuner, OptunaBayesianTuner

def test_competition_platform():
    print(">>> 測試 2.1：多模型分類與回歸競賽平台 (MLCompetitionPlatform)...")
    # 建立分類虛擬特徵與目標
    np.random.seed(42)
    X_cls = np.random.normal(0, 1, (150, 4))
    y_cls = (X_cls[:, 0] + 0.5 * X_cls[:, 1] > 0.2).astype(int)
    
    platform = MLCompetitionPlatform()
    
    # 測試分類器對比
    cls_results = platform.run_classification_competition(X_cls, y_cls)
    print("  分類競賽前 5 排名（含 Stacking/MLP）：")
    for r in cls_results[:5]:
        print(f"    - 模型: {r['model']:<20} | F1-Score (Macro): {r['f1_macro']:.4f}")
        
    assert len(cls_results) > 0, "無分類競賽結果！"
    assert any(r["model"] == "StackingClassifier" for r in cls_results), "缺少 Stacking 分類器！"
    
    # 建立回歸虛擬特徵與目標 (模擬 RUL 壽命預估)
    X_reg = np.random.normal(0, 1, (100, 4))
    y_reg = 100.0 - 5.0 * X_reg[:, 0] - 2.5 * X_reg[:, 1] + np.random.normal(0, 0.5, 100)
    
    reg_results = platform.run_regression_competition(X_reg, y_reg)
    print("\n  回歸競賽前 5 排名（RUL 預估）：")
    for r in reg_results[:5]:
        print(f"    - 模型: {r['model']:<20} | R2-Score: {r['r2_score']:.4f}")
        
    assert len(reg_results) > 0, "無回歸競賽結果！"
    assert any(r["model"] == "StackingRegressor" for r in reg_results), "缺少 Stacking 回歸器！"
    print("  [PASS] 多模型競賽平台測試通過！")

def test_unsupervised_clustering():
    print("\n>>> 測試 2.2：無監督異常分群與 Silhouette 評估 (OPTICS/Birch/Spectral)...")
    np.random.seed(42)
    g1 = np.random.normal([0, 0], 0.2, (30, 2))
    g2 = np.random.normal([5, 5], 0.2, (30, 2))
    g3 = np.random.normal([0, 5], 0.2, (30, 2))
    g4 = np.random.normal([5, 0], 0.2, (30, 2))
    X = np.vstack([g1, g2, g3, g4])
    
    clusterer = UnsupervisedClustering(n_clusters=4)
    
    # 測試各模型分群與評估
    models = {
        "K-Means": clusterer.fit_kmeans(X),
        "DBSCAN": clusterer.fit_dbscan(X, eps=1.0, min_samples=3),
        "Birch": clusterer.fit_birch(X),
        "OPTICS": clusterer.fit_optics(X, min_samples=3),
        "Spectral": clusterer.fit_spectral(X)
    }
    
    for name, (labels, score) in models.items():
        print(f"    - {name:<10} Silhouette Score: {score:.4f}")
        assert score > -0.5, f"{name} 分群執行異常！"
        
    print("  [PASS] 多種無監督分群測試通過！")

def test_genetic_tuner():
    print("\n>>> 測試 2.3：遺傳演算法超參數尋優 (GeneticAlgorithmTuner)...")
    np.random.seed(42)
    X = np.random.normal(0, 1, (100, 4))
    y = (X[:, 0] * 1.5 + X[:, 1] > 0.0).astype(int)
    
    tuner = GeneticAlgorithmTuner(X, y, pop_size=6, generations=4, mutation_rate=0.2)
    best_params, best_fit = tuner.tune()
    
    print("  GA 尋優最佳參數：")
    for k, v in best_params.items():
        print(f"    - {k}: {v}")
    print(f"  最佳 F1 適應度 (Fitness): {best_fit:.4f}")
    
    assert best_fit > 0.5, "GA 未能收斂出合適適應度！"
    print("  [PASS] GA 遺傳超參數尋優測試通過！")

def test_optuna_tuner():
    print("\n>>> 測試 2.4：Optuna 貝氏 (SMAC/TPE) 超參數尋優 (OptunaBayesianTuner)...")
    np.random.seed(42)
    X = np.random.normal(0, 1, (100, 4))
    y = (X[:, 0] * 1.5 + X[:, 1] > 0.0).astype(int)
    
    tuner = OptunaBayesianTuner(X, y, n_trials=8)
    best_params, best_fit = tuner.tune()
    
    print("  Optuna-TPE 尋優最佳參數：")
    for k, v in best_params.items():
        print(f"    - {k}: {v}")
    print(f"  最佳 F1 適應度 (Fitness): {best_fit:.4f}")
    
    assert best_fit > 0.5, "Optuna-TPE 未能收斂出合適適應度！"
    print("  [PASS] Optuna-TPE 貝氏超參數尋優測試通過！")

<<<<<<< HEAD
def test_imbalanced_learning():
    print("\n>>> 測試 2.5：極度類別不平衡下的分類競賽與過採樣 (SMOTE/Class-Weighted)...")
    # 建立高度不平衡數據集 (模擬 LN 正常佔 97%，LO 早期退化僅佔 3%)
    np.random.seed(42)
    n_samples = 500
    n_minority = 15 # 3% 的少數類
    
    # 多數類 (LN)
    X_majority = np.random.normal(0, 1.0, (n_samples - n_minority, 4))
    y_majority = np.zeros(n_samples - n_minority, dtype=int)
    
    # 少數類 (LO) - 均值有微小偏移，且加入高峭度脈衝
    X_minority = np.random.normal(0.5, 1.0, (n_minority, 4))
    y_minority = np.ones(n_minority, dtype=int)
    
    X = np.vstack([X_majority, X_minority])
    y = np.concatenate([y_majority, y_minority])
    
    platform = MLCompetitionPlatform()
    results = platform.run_classification_competition(X, y)
    
    print("  高度失衡下 (3% 早期故障樣本) 的分類模型 Macro F1-Score 排名：")
    for r in results[:5]:
        print(f"    - 模型: {r['model']:<25} | F1-Score (Macro): {r['f1_macro']:.4f}")
        
    # 斷言最佳模型的 Macro F1-Score 應在合理範圍內
    # 由於隨機噪聲，如果完全不處理失衡，Macro F1 通常會因為忽略少數類而跌至 ~0.45。
    # 透過 class_weight 與 oversampling，最佳模型應能突破 0.50 以上。
    best_f1 = results[0]["f1_macro"]
    assert best_f1 > 0.48, f"不平衡分類優化效果不佳，最佳 F1 僅為: {best_f1:.4f}"
    print("  [PASS] 類別不平衡與代價敏感學習測試通過！")

=======
>>>>>>> b5a207cdbbbcb9a64bd2e230beb9283139dc051a
if __name__ == "__main__":
    test_competition_platform()
    test_unsupervised_clustering()
    test_genetic_tuner()
    test_optuna_tuner()
<<<<<<< HEAD
    test_imbalanced_learning()
=======
>>>>>>> b5a207cdbbbcb9a64bd2e230beb9283139dc051a
