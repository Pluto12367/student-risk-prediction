# -*- coding: utf-8 -*-
"""
train.py —— 模型训练 + Optuna 调参 + MLflow 实验追踪 + 代价敏感阈值优化

运行:
    python src/train.py --baseline        # 4 个模型基线对比 (全部记录 MLflow)
    python src/train.py --tune            # Optuna 调参 LightGBM, 回填 best.yaml
    python src/train.py --config configs/best.yaml   # 用最优配置复现

所有实验记录到 MLflow (./mlruns), 查看: mlflow ui --backend-store-uri ./mlruns
"""

import argparse
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "configs" / "best.yaml"


# ---------------------------------------------------------------- 数据准备
def load_data():
    df = pd.read_csv(BASE / "data" / "processed" / "model.csv")
    y = df["label"]
    X = df.drop(columns=["label", "risk_level"])
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)


# ---------------------------------------------------------------- 模型工厂
def build_model(name: str, params: dict | None = None, seed: int = 42):
    params = params or {}
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(),
                             LogisticRegression(max_iter=1000, random_state=seed))
    if name == "random_forest":
        return RandomForestClassifier(random_state=seed, **params)
    if name == "xgboost":
        return XGBClassifier(random_state=seed, eval_metric="logloss",
                             **params)
    if name == "lightgbm":
        return LGBMClassifier(random_state=seed, verbose=-1, **params)
    raise ValueError(f"未知模型: {name}")


# ---------------------------------------------------------------- 评估
def evaluate(model, X_te, y_te, threshold=0.5) -> dict:
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "auc": roc_auc_score(y_te, proba),
        "f1": f1_score(y_te, pred, zero_division=0),
        "precision": precision_score(y_te, pred, zero_division=0),
        "recall": recall_score(y_te, pred, zero_division=0),
    }


def optimize_threshold(model, X_tr, y_tr, fn_cost: float = 5.0) -> float:
    """代价敏感阈值: 漏报一个高危学生的代价按 fn_cost 倍惩罚,
    在训练集内网格搜索使总代价最小的阈值。"""
    proba = model.predict_proba(X_tr)[:, 1]
    best_t, best_cost = 0.5, np.inf
    for t in np.arange(0.05, 0.95, 0.01):
        pred = (proba >= t).astype(int)
        fp = int(((pred == 1) & (y_tr == 0)).sum())
        fn = int(((pred == 0) & (y_tr == 1)).sum())
        cost = fp + fn_cost * fn
        if cost < best_cost:
            best_t, best_cost = float(t), cost
    return best_t


# ---------------------------------------------------------------- MLflow
def log_run(run_name: str, model, params: dict, metrics: dict,
            extra: dict | None = None):
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if extra:
            mlflow.log_metrics(extra)
        mlflow.sklearn.log_model(model, name="model", serialization_format="cloudpickle")
    print(f"[{run_name}] " + " ".join(f"{k}={v:.4f}" for k, v in metrics.items()))


def setup_mlflow(cfg: dict):
    uri = cfg["mlflow"]["tracking_uri"]
    if not uri.startswith(("sqlite:", "postgresql:", "mysql:", "http:", "https:")):
        uri = (BASE / uri).as_uri()
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(cfg["mlflow"]["experiment_name"])


# ---------------------------------------------------------------- 流程
def run_baseline(cfg: dict) -> pd.DataFrame:
    """4 模型基线对比, 全部记录 MLflow, 返回指标表。"""
    X_tr, X_te, y_tr, y_te = load_data()
    rows = []
    for name in ["logistic_regression", "random_forest", "xgboost", "lightgbm"]:
        model = build_model(name, seed=cfg["random_state"])
        model.fit(X_tr, y_tr)
        metrics = evaluate(model, X_te, y_te)
        log_run(f"baseline_{name}", model, {"model": name}, metrics)
        rows.append({"model": name, **metrics})
    result = pd.DataFrame(rows).sort_values("auc", ascending=False)
    print("\n== 基线对比 ==")
    print(result.round(4).to_string(index=False))
    result.to_csv(BASE / "reports" / "baseline_results.csv", index=False)
    return result


def run_tune(cfg: dict, n_trials: int = 40) -> None:
    """Optuna 调参 LightGBM, 记录 MLflow 并回填 best.yaml。"""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    X_tr, X_te, y_tr, y_te = load_data()
    X_tr2, X_val, y_tr2, y_val = train_test_split(
        X_tr, y_tr, test_size=0.2, random_state=42, stratify=y_tr)

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 40),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        }
        model = build_model("lightgbm", params)
        model.fit(X_tr2, y_tr2)
        return roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    best = study.best_params
    print(f"[optuna] best auc={study.best_value:.4f} params={best}")

    # 用最优参数在全训练集重训并评估
    model = build_model("lightgbm", best)
    model.fit(X_tr, y_tr)
    metrics = evaluate(model, X_te, y_te)
    threshold = optimize_threshold(model, X_tr, y_tr)
    tuned = evaluate(model, X_te, y_te, threshold=threshold)
    log_run("tuned_lightgbm", model, best, metrics,
            extra={"threshold": threshold,
                   **{f"tuned_{k}": v for k, v in tuned.items()}})
    print(f"[tuned@thr={threshold:.2f}] " +
          " ".join(f"{k}={v:.4f}" for k, v in tuned.items()))

    # 回填 best.yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["params"] = {k: (float(v) if isinstance(v, float) else int(v))
                     for k, v in best.items()}
    cfg["risk_threshold"]["high"] = round(threshold, 2)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    print(f"[saved] 最优参数已回填 {CONFIG_PATH}")


def run_reproduce(cfg: dict) -> None:
    """用 best.yaml 配置复现最终实验。"""
    X_tr, X_te, y_tr, y_te = load_data()
    model = build_model(cfg["model"], cfg["params"], seed=cfg["random_state"])
    model.fit(X_tr, y_tr)
    thr = cfg["risk_threshold"]["high"]
    metrics = evaluate(model, X_te, y_te)
    tuned = evaluate(model, X_te, y_te, threshold=thr)
    log_run("reproduce_best", model, cfg["params"], metrics,
            extra={f"thr_{k}": v for k, v in tuned.items()})
    print(f"[reproduce@thr={thr:.2f}] " +
          " ".join(f"{k}={v:.4f}" for k, v in tuned.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--tune", action="store_true")
    parser.add_argument("--n-trials", type=int, default=40)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    setup_mlflow(cfg)

    if args.baseline:
        run_baseline(cfg)
    elif args.tune:
        run_tune(cfg, args.n_trials)
    else:
        run_reproduce(cfg)
