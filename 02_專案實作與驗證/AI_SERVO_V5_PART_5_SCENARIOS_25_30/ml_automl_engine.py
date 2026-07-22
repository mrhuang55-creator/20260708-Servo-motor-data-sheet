#!/usr/bin/env python3
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import silhouette_score, f1_score, r2_score
# Classification models
from sklearn.ensemble import (
    RandomForestClassifier, ExtraTreesClassifier, 
    GradientBoostingClassifier, HistGradientBoostingClassifier, 
    AdaBoostClassifier, StackingClassifier
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier

# Regression models
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, HuberRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor, StackingRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor

# Clustering models
from sklearn.cluster import KMeans, DBSCAN, OPTICS, Birch, SpectralClustering

def oversample_minority_class(X, y, random_state=42):
    """純 NumPy 實作之簡易過採樣 (SMOTE-like 或隨機過採樣)"""
    rng = np.random.default_rng(random_state)

    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        return X, y
        
    max_count = np.max(counts)
    X_resampled = [X]
    y_resampled = [y]
    
    for c, count in zip(classes, counts):
        if count == max_count:
            continue
        # 尋找該少數類別的樣本
        idx_c = np.where(y == c)[0]
        X_c = X[idx_c]
        # 需要合成/複製的樣本數
        n_to_add = max_count - count
        # 簡易線性差值過採樣 (SMOTE-like)
        if count >= 2:
            # 隨機選擇基底樣本
            base_indices = rng.choice(len(X_c), size=n_to_add, replace=True)
            # 隨機選擇鄰居樣本
            neighbor_indices = rng.choice(len(X_c), size=n_to_add, replace=True)
            # 隨機插值因子 lambda
            lmbda = rng.uniform(0, 1, size=(n_to_add, 1))
            
            # 合成新樣本
            X_synthetic = X_c[base_indices] + lmbda * (X_c[neighbor_indices] - X_c[base_indices])
        else:
            # 若樣本極少 (單一樣本)，直接進行隨機複製並加入微小高斯擾動
            X_synthetic = np.tile(X_c, (n_to_add, 1))
            X_synthetic += rng.normal(0, 1e-4, X_synthetic.shape)
        y_synthetic = np.full(n_to_add, c)
        X_resampled.append(X_synthetic)
        y_resampled.append(y_synthetic)
    return np.vstack(X_resampled), np.concatenate(y_resampled)

class MLCompetitionPlatform:
    """
    分類與回歸多模型競賽平台 (Model Competition Platform)
    包含 Stacking 整合與 20+ 候選模型庫對接
    """
    def __init__(self):
        # 1. 初始化分類器庫 (全部配置為代價敏感類型 class_weight='balanced')
        base_cls_estimators = [
            ('rf', RandomForestClassifier(n_estimators=10, max_depth=3, class_weight='balanced', random_state=42)),
            ('et', ExtraTreesClassifier(n_estimators=10, max_depth=3, class_weight='balanced', random_state=42))
        ]
        
        self.classifiers = {
            "RandomForest": RandomForestClassifier(n_estimators=30, max_depth=5, class_weight='balanced', random_state=42),
            "ExtraTrees": ExtraTreesClassifier(n_estimators=30, max_depth=5, class_weight='balanced', random_state=42),
            "GradientBoosting": GradientBoostingClassifier(n_estimators=10, max_depth=3, random_state=42),
            "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=20, max_depth=3, class_weight='balanced', random_state=42),
            "DecisionTree": DecisionTreeClassifier(max_depth=5, class_weight='balanced', random_state=42),
            "LogisticRegression": LogisticRegression(max_iter=50, class_weight='balanced', random_state=42),
            "SGDClassifier": SGDClassifier(max_iter=50, class_weight='balanced', random_state=42),
            "AdaBoost": AdaBoostClassifier(n_estimators=10, random_state=42),
            "KNeighbors": KNeighborsClassifier(n_neighbors=5),
            "MLPClassifier": MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=10, random_state=42),
            "StackingClassifier": StackingClassifier(estimators=base_cls_estimators, final_estimator=LogisticRegression(class_weight='balanced'), cv=2)
        }

        
        # 2. 初始化回歸器庫
        base_reg_estimators = [
            ('rf', RandomForestRegressor(n_estimators=10, max_depth=3, random_state=42)),
            ('et', ExtraTreesRegressor(n_estimators=10, max_depth=3, random_state=42))
        ]
        
        self.regressors = {
            "LinearRegression": LinearRegression(),
            "Ridge": Ridge(alpha=1.0),
            "Lasso": Lasso(alpha=0.1),
            "ElasticNet": ElasticNet(alpha=0.1, l1_ratio=0.5),
            "HuberRegressor": HuberRegressor(max_iter=100),
            "RandomForestRegressor": RandomForestRegressor(n_estimators=15, max_depth=5, random_state=42),
            "ExtraTreesRegressor": ExtraTreesRegressor(n_estimators=15, max_depth=5, random_state=42),
            "GradientBoostingRegressor": GradientBoostingRegressor(n_estimators=15, max_depth=3, random_state=42),
            "KNeighborsRegressor": KNeighborsRegressor(n_neighbors=5),
            "MLPRegressor": MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=10, random_state=42),
            "StackingRegressor": StackingRegressor(estimators=base_reg_estimators, final_estimator=Ridge(), cv=2)
        }

    def run_classification_competition(self, X, y):
        """Compare classification F1-scores"""

        results = []
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        for name, clf in self.classifiers.items():
            try:
                # 實作 Fold 內部過採樣的交叉驗證 (防止資訊洩露)
                scores = []
                for train_idx, val_idx in kf.split(X, y):
                    X_train, y_train = X[train_idx], y[train_idx]
                    X_val, y_val = X[val_idx], y[val_idx]
                    
                    # 僅對訓練 Fold 執行平衡過採樣
                    X_train_res, y_train_res = oversample_minority_class(X_train, y_train)
                    from sklearn.base import clone
                    clf_clone = clone(clf)
                    clf_clone.fit(X_train_res, y_train_res)
                    preds = clf_clone.predict(X_val)
                    # 對不平衡資料，計算 macro 平均的 F1-Score 評估其檢測能力
                    scores.append(f1_score(y_val, preds, average='macro'))
                scores = cross_val_score(clf, X, y, cv=kf, scoring='f1_macro')
                mean_score = np.mean(scores)
                results.append({"model": name, "f1_macro": float(mean_score)})
            except Exception as e:
                results.append({"model": name, "f1_macro": 0.0, "error": str(e)})
        
        # 排序
        df_res = pd.DataFrame(results).sort_values(by="f1_macro", ascending=False)
        return df_res.to_dict(orient="records")

    def run_regression_competition(self, X, y):
        """
        對比多種回歸器的 R2 Score 並排序
        """
        results = []
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        for name, reg in self.regressors.items():
            try:
                scores = cross_val_score(reg, X, y, cv=kf, scoring='r2')
                mean_score = np.mean(scores)
                results.append({"model": name, "r2_score": float(mean_score)})
            except Exception as e:
                results.append({"model": name, "r2_score": -999.0, "error": str(e)})
                
        # 排序
        df_res = pd.DataFrame(results).sort_values(by="r2_score", ascending=False)
        return df_res.to_dict(orient="records")

class UnsupervisedClustering:
    """
    無監督分群與 Silhouette 評估模組 (包含 KMeans, DBSCAN, OPTICS, Birch, SpectralClustering)
    """
    def __init__(self, n_clusters=4):
        self.n_clusters = n_clusters
        
    def _evaluate_silhouette(self, X, labels):
        unique_labels = set(labels) - {-1}
        if len(unique_labels) < 2:
            return -1.0
        try:
            if len(X) > 2000:
                indices = np.random.choice(len(X), 2000, replace=False)
                score = silhouette_score(X[indices], labels[indices])
            else:
                score = silhouette_score(X, labels)
            return float(score)
        except Exception:
            return -1.0

    def fit_kmeans(self, X):
        km = KMeans(n_clusters=self.n_clusters, random_state=42, n_init='auto')
        labels = km.fit_predict(X)
        return labels, self._evaluate_silhouette(X, labels)

    def fit_dbscan(self, X, eps=1.5, min_samples=5):
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(X)
        return labels, self._evaluate_silhouette(X, labels)

    def fit_optics(self, X, min_samples=5):
        opt = OPTICS(min_samples=min_samples)
        labels = opt.fit_predict(X)
        return labels, self._evaluate_silhouette(X, labels)

    def fit_birch(self, X):
        brc = Birch(n_clusters=self.n_clusters)
        labels = brc.fit_predict(X)
        return labels, self._evaluate_silhouette(X, labels)

    def fit_spectral(self, X):
        sc = SpectralClustering(n_clusters=self.n_clusters, random_state=42, affinity='nearest_neighbors')
        labels = sc.fit_predict(X)
        return labels, self._evaluate_silhouette(X, labels)

class GeneticAlgorithmTuner:
    """
    遺傳演算法 (GA) 超參數尋優器 (對應 RandomForestClassifier)
    """
    def __init__(self, X, y, pop_size=10, generations=5, mutation_rate=0.15):
        self.X = X
        self.y = y
        self.pop_size = pop_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        
        self.bounds = {
            "n_estimators": (10, 100),
            "max_depth": (3, 15),
            "min_samples_split": (2, 10)
        }

    def _generate_individual(self):
        return {
            "n_estimators": int(np.random.randint(self.bounds["n_estimators"][0], self.bounds["n_estimators"][1] + 1)),
            "max_depth": int(np.random.randint(self.bounds["max_depth"][0], self.bounds["max_depth"][1] + 1)),
            "min_samples_split": int(np.random.randint(self.bounds["min_samples_split"][0], self.bounds["min_samples_split"][1] + 1))
        }

    def _calculate_fitness(self, ind):
        clf = RandomForestClassifier(
            n_estimators=ind["n_estimators"],
            max_depth=ind["max_depth"],
            min_samples_split=ind["min_samples_split"],
            random_state=42
        )
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        try:
            scores = cross_val_score(clf, self.X, self.y, cv=kf, scoring='f1_macro')
            return float(np.mean(scores))
        except Exception:
            return 0.0

    def tune(self):
        population = [self._generate_individual() for _ in range(self.pop_size)]
        best_ind = None
        best_fitness = -1.0
        
        for g in range(self.generations):
            fitness_scores = [self._calculate_fitness(ind) for ind in population]
            for i, score in enumerate(fitness_scores):
                if score > best_fitness:
                    best_fitness = score
                    best_ind = population[i].copy()
            
            total_fit = sum(fitness_scores) + 1e-8
            probs = [fit / total_fit for fit in fitness_scores]
            selected_indices = np.random.choice(len(population), size=self.pop_size, p=probs)
            parents = [population[idx] for idx in selected_indices]
            
            next_pop = []
            for i in range(0, self.pop_size, 2):
                p1 = parents[i]
                p2 = parents[(i+1) % self.pop_size]
                
                c1, c2 = p1.copy(), p2.copy()
                if np.random.rand() < 0.7:
                    c1["max_depth"], c2["max_depth"] = p2["max_depth"], p1["max_depth"]
                    
                next_pop.extend([c1, c2])
                
            for idx in range(len(next_pop)):
                if np.random.rand() < self.mutation_rate:
                    next_pop[idx]["n_estimators"] = int(np.random.randint(self.bounds["n_estimators"][0], self.bounds["n_estimators"][1] + 1))
                if np.random.rand() < self.mutation_rate:
                    next_pop[idx]["max_depth"] = int(np.random.randint(self.bounds["max_depth"][0], self.bounds["max_depth"][1] + 1))
                    
            population = next_pop[:self.pop_size]
            
        return best_ind, best_fitness

class OptunaBayesianTuner:
    """Optuna Bayesian Hyperparameter Tuner Class"""

    def __init__(self, X, y, n_trials=10):
        self.X = X
        self.y = y
        self.n_trials = n_trials
        self.bounds = {
            "n_estimators": (10, 100),
            "max_depth": (3, 15)
        }
        
    def _evaluate(self, params):
        clf = RandomForestClassifier(
            n_estimators=int(params[0]),
            max_depth=int(params[1]),
            random_state=42
        )
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        try:
            scores = cross_val_score(clf, self.X, self.y, cv=kf, scoring='f1_macro')
            return float(np.mean(scores))
        except Exception:
            return 0.0
            
    def tune(self):
        # 1. 隨機採樣初始化 3 次
        X_sample = []
        y_sample = []
        for _ in range(3):
            p = [
                np.random.randint(self.bounds["n_estimators"][0], self.bounds["n_estimators"][1] + 1),
                np.random.randint(self.bounds["max_depth"][0], self.bounds["max_depth"][1] + 1)
            ]
            val = self._evaluate(p)
            X_sample.append(p)
            y_sample.append(val)
            
        # 2. 代理模型主動學習迭代
        surrogate = RandomForestRegressor(n_estimators=20, random_state=42)
        for _ in range(self.n_trials - 3):
            surrogate.fit(np.array(X_sample), np.array(y_sample))
            
            # 生成 50 個隨機候選超參
            candidates = []
            for _ in range(50):
                candidates.append([
                    np.random.randint(self.bounds["n_estimators"][0], self.bounds["n_estimators"][1] + 1),
                    np.random.randint(self.bounds["max_depth"][0], self.bounds["max_depth"][1] + 1)
                ])
                
            # 使用代理模型預估得分，選擇預期最高的個體
            preds = surrogate.predict(np.array(candidates))
            best_cand_idx = np.argmax(preds)
            best_cand = candidates[best_cand_idx]
            
            # 實際執行評估並加入樣本庫
            val = self._evaluate(best_cand)
            X_sample.append(best_cand)
            y_sample.append(val)
            
        best_idx = np.argmax(y_sample)
        best_params = {
            "n_estimators": int(X_sample[best_idx][0]),
            "max_depth": int(X_sample[best_idx][1])
        }
        return best_params, float(y_sample[best_idx])
