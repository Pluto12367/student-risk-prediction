# -*- coding: utf-8 -*-
"""
explain.py —— SHAP 模型解释 (全局特征重要性 + 个体预警解释)

运行: python src/explain.py
输出: reports/figures/fig_4-*.png + 控制台个体解释
"""

import matplotlib.pyplot as plt
import pandas as pd
import shap
import yaml

from src.data import BASE
from src.train import build_model, load_data
from src.viz import PALETTE, FigureManager


def main() -> None:
    with open(BASE / "configs" / "best.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    X_tr, X_te, y_tr, y_te = load_data()
    model = build_model(cfg["model"], cfg["params"], seed=cfg["random_state"])
    model.fit(X_tr, y_tr)

    # LightGBM 原生 predict_proba 供 TreeExplainer
    booster = model.named_steps["model"] if hasattr(model, "named_steps") else model
    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(X_te)
    # 二分类时 shap_values 返回 [class0, class1] 或单个数组
    sv = shap_values[1] if isinstance(shap_values, list) else shap_values

    fm = FigureManager(chapter=4)   # 模型解释 = 第 4 章

    # 图4-1 全局特征重要性 (条形图: 平均 |SHAP|)
    fig = plt.figure()
    shap.summary_plot(sv, X_te, max_display=10, show=False,
                      plot_type="bar", plot_size=None)
    # 统一配色: 把 SHAP 默认亮蓝换成项目主色
    for patch in plt.gca().patches:
        patch.set_facecolor(PALETTE["primary"])
    fm.save(fig, plt.gca(), title="SHAP 全局特征重要性 Top10",
            caption="图注：条形长度为平均 |SHAP| 值, 表示特征对'高危'预测的平均贡献强度。")

    # 图4-2 SHAP 蜂群图 (带影响方向)
    fig = plt.figure()
    shap.summary_plot(sv, X_te, max_display=10, show=False, plot_size=None)
    fm.save(fig, plt.gca(), title="SHAP 特征影响方向",
            caption="图注：点色表示特征取值高低(红高蓝低), 点在右侧表示推高高危概率, 左侧表示降低。")

    # 个体解释: 取测试集中预测风险最高的样本
    proba = model.predict_proba(X_te)[:, 1]
    idx = int(proba.argmax())
    print(f"\n== 个体解释 (样本 #{idx}, 高危概率={proba[idx]:.2%}) ==")
    contrib = pd.Series(sv[idx], index=X_te.columns).sort_values()
    for title, top3 in [("推高风险 Top3", contrib.tail(3)[::-1]),
                        ("降低风险 Top3", contrib.head(3))]:
        print(f"{title}:")
        for feat, val in top3.items():
            print(f"  {feat} (取值={X_te.iloc[idx][feat]})  SHAP={val:+.3f}")

    # 图4-3 个体 force plot
    shap.force_plot(explainer.expected_value if not isinstance(explainer.expected_value, list)
                    else explainer.expected_value[1],
                    sv[idx], X_te.iloc[idx], matplotlib=True, show=False)
    fm.save(plt.gcf(), plt.gca(), title=f"个案解释：样本 #{idx}",
            caption="图注：红色特征推高高危概率, 蓝色特征降低, 供辅导员生成干预建议。")

    print("\nSHAP 解释完成, 图表已保存至 reports/figures/")


if __name__ == "__main__":
    main()
