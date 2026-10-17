# -*- coding: utf-8 -*-
"""shap_values.py —— 导出真实 SHAP 平均贡献值, 供图表与报告引用。"""

import json
from pathlib import Path

import pandas as pd
import shap
import yaml

from src.train import build_model, load_data

BASE = Path(__file__).resolve().parent.parent


def main():
    with open(BASE / "configs" / "best.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    X_tr, X_te, y_tr, y_te = load_data()
    model = build_model(cfg["model"], cfg["params"], seed=cfg["random_state"])
    model.fit(X_tr, y_tr)
    booster = model.named_steps["model"] if hasattr(model, "named_steps") else model
    explainer = shap.TreeExplainer(booster)
    sv = explainer.shap_values(X_te)
    sv = sv[1] if isinstance(sv, list) else sv
    mean_abs = pd.Series(abs(sv).mean(axis=0), index=X_te.columns).sort_values(ascending=False)
    top = {k: round(float(v), 3) for k, v in mean_abs.head(10).items()}
    out = BASE / "reports" / "shap_importance.json"
    out.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(top, ensure_ascii=False, indent=2))
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
