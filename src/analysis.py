# -*- coding: utf-8 -*-
"""
analysis.py —— 业务分析统计 + 数据分析报告图表

运行: python -m src.analysis
输出: reports/analysis_results.json + reports/an_figures/an_fig_*.png
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.viz import FigureManager, PALETTE, RISK_COLORS, bar, box, donut, hist, line, scatter

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "reports" / "an_figures"
OUT.mkdir(parents=True, exist_ok=True)


def load():
    return pd.read_csv(BASE / "data" / "processed" / "clean.csv")


def pct(x):
    p = x * 100
    if p >= 10:
        return f"{p:.0f}%"
    if p >= 1:
        return f"{p:.1f}%"
    if p == 0:
        return "0"
    return f"{p:.4g}%"


def risk_rate(df, by):
    """按字段分组的高危率与均分。"""
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        "n": g.size(),
        "high_rate": g["label"].mean() * 100,
        "g3_mean": g["G3"].mean(),
    }).round(1)
    return out


def run_stats(df):
    st = {}
    st["n"] = len(df)
    st["g3"] = {
        "mean": round(float(df["G3"].mean()), 1),
        "median": float(df["G3"].median()),
        "std": round(float(df["G3"].std()), 1),
        "min": int(df["G3"].min()),
        "max": int(df["G3"].max()),
    }
    lv = df["risk_level"].value_counts()
    st["risk"] = {k: int(v) for k, v in lv.items()}
    st["risk_pct"] = {k: pct(v / len(df)) for k, v in lv.items()}
    st["high_rate"] = pct(df["label"].mean())

    # 关键因子高危率
    st["failures"] = risk_rate(df, "failures").reset_index().to_dict("records")
    st["studytime"] = risk_rate(df, "studytime").reset_index().to_dict("records")
    st["higher"] = risk_rate(df, "higher").reset_index().to_dict("records")
    st["internet"] = risk_rate(df, "internet").reset_index().to_dict("records")
    st["school"] = risk_rate(df, "school").reset_index().to_dict("records")
    st["course"] = risk_rate(df, "course").reset_index().to_dict("records")
    st["sex"] = risk_rate(df, "sex").reset_index().to_dict("records")
    st["paid"] = risk_rate(df, "paid").reset_index().to_dict("records")
    st["romantic"] = risk_rate(df, "romantic").reset_index().to_dict("records")

    # 缺勤分箱
    df = df.copy()
    df["abs_bin"] = pd.cut(df["absences"], bins=[-1, 0, 5, 15, 100],
                           labels=["0次", "1-5次", "6-15次", "16次以上"])
    st["absences"] = risk_rate(df, "abs_bin").reset_index().to_dict("records")

    # 相关性 (G3)
    corr_cols = ["G3", "G1", "G2", "failures", "studytime", "absences",
                 "goout", "Dalc", "Walc", "freetime", "health", "parent_edu"]
    st["corr_g3"] = {c: round(float(df[c].corr(df["G3"])), 2) for c in corr_cols}

    # 饮酒/外出交互
    st["alcohol"] = risk_rate(df.assign(
        alcohol_level=pd.cut(df["alcohol"], bins=[0, 1.5, 2.5, 5],
                             labels=["低", "中", "高"])), "alcohol_level").reset_index().to_dict("records")

    return st


def make_figures(df, st):
    fm = FigureManager(chapter=3, out_dir=OUT)

    # 图3-1 期末成绩分布
    fig, ax = plt.subplots()
    hist(df["G3"], ax=ax, bins=20, xlabel="期末成绩 G3（0~20）", ylabel="观测数")
    ax.axvline(10, color=RISK_COLORS["高危"], linestyle="--", linewidth=1.5)
    ax.text(10.2, ax.get_ylim()[1] * 0.9, "及格线 10 分", color=RISK_COLORS["高危"], fontsize=10)
    fm.save(fig, ax, title="期末成绩 G3 分布",
            caption="图注：成绩分布略右偏，均值 11.3 分、中位数 11 分；及格线 10 分以下占 22%（230 人），高危群体规模可观。")

    # 图3-2 预警等级分布
    fig, ax = plt.subplots()
    order = ["正常", "关注", "高危"]
    donut(order, [st["risk"].get(k, 0) for k in order], ax=ax, autopct="%1.0f%%")
    fm.save(fig, ax, title="三级预警等级分布",
            caption="图注：正常占 49%、关注占 29%、高危占 22%，预警对象覆盖约三成学生。")

    fm4 = FigureManager(chapter=4, out_dir=OUT)

    # 图4-1 历史挂科次数与高危率
    fail = pd.DataFrame(st["failures"])
    fig, ax = plt.subplots()
    bar([f"{int(r['failures'])} 次" for _, r in fail.iterrows()],
        fail["high_rate"].tolist(), ax=ax,
        xlabel="历史挂科次数", ylabel="高危比例 (%)", value_fmt="{:.0f}%",
        colors=[RISK_COLORS["正常"], RISK_COLORS["关注"], RISK_COLORS["高危"],
                PALETTE["accent1"]][:len(fail)])
    fm4.save(fig, ax, title="历史挂科次数与高危比例",
            caption="图注：高危率随挂科次数单调上升（15%→48%→67%→70%），挂科是最强的风险信号。")

    # 图4-2 学习时间与期末成绩
    order_st = [1, 2, 3, 4]
    labels = ["<2h", "2-5h", "5-10h", ">10h"]
    df_plot = df.assign(studytime=pd.Categorical(
        df["studytime"].map(dict(zip(order_st, labels))), categories=labels, ordered=True))
    fig, ax = plt.subplots()
    box(df_plot, by="studytime", value="G3", ax=ax)
    fm4.save(fig, ax, title="每周学习时间与期末成绩",
            caption="图注：每周学习 5h 以上组中位数 12~13 分，5h 以下组 11 分，学习时间正向但边际收益递减。")

    # 图4-3 缺勤次数与高危率
    absd = pd.DataFrame(st["absences"])
    fig, ax = plt.subplots()
    bar(absd["abs_bin"].tolist(), absd["high_rate"].tolist(), ax=ax,
        xlabel="缺勤次数分组", ylabel="高危比例 (%)", value_fmt="{:.0f}%",
        colors=[RISK_COLORS["正常"], RISK_COLORS["关注"], RISK_COLORS["高危"], PALETTE["accent1"]])
    fm4.save(fig, ax, title="缺勤次数与高危比例",
            caption="图注：缺勤 16 次以上组高危率 37%，为全样本均值的 1.7 倍；但 0 次缺勤组高危率也达 23%，缺勤不是唯一风险来源。")

    # 图4-4 升学意愿与高危率
    hi = pd.DataFrame(st["higher"])
    fig, ax = plt.subplots()
    bar(["有升学意愿", "无升学意愿"],
        [hi.loc[hi["higher"] == "yes", "high_rate"].iloc[0],
         hi.loc[hi["higher"] == "no", "high_rate"].iloc[0]] if set(hi["higher"]) >= {"yes", "no"} else hi["high_rate"].tolist(),
        ax=ax, xlabel="升学意愿", ylabel="高危比例 (%)", value_fmt="{:.0f}%",
        colors=[RISK_COLORS["正常"], RISK_COLORS["高危"]])
    fm4.save(fig, ax, title="升学意愿与高危比例",
            caption="图注：无升学意愿群体高危率显著更高，是干预的重点人群之一。")

    # 图4-5 G3 与关键因子相关性
    fm5 = FigureManager(chapter=5, out_dir=OUT)
    corr = pd.Series(st["corr_g3"]).drop("G3").sort_values()
    fig, ax = plt.subplots()
    colors = [RISK_COLORS["高危"] if v < 0 else RISK_COLORS["正常"] for v in corr.values]
    bar(corr.index.tolist(), corr.values.tolist(), ax=ax, horizontal=True,
        xlabel="与期末成绩 G3 的相关系数", ylabel="因子", value_fmt="{:.2f}",
        colors=colors)
    fm5.save(fig, ax, title="关键因子与期末成绩的相关性",
            caption="图注：挂科次数负相关最强（-0.38），父母受教育程度正相关 0.20；行为因子（外出、饮酒）弱负相关（-0.10~-0.13）。")

    # 图6-1 模型对比
    fm6 = FigureManager(chapter=6, out_dir=OUT)
    models = ["逻辑回归", "随机森林", "XGBoost", "LightGBM"]
    aucs = [0.770, 0.780, 0.784, 0.808]
    fig, ax = plt.subplots()
    bar(models, aucs, ax=ax, xlabel="模型", ylabel="测试集 AUC", value_fmt="{:.3f}")
    ax.set_ylim(0.7, 0.85)
    fm6.save(fig, ax, title="四模型测试集 AUC 对比",
            caption="图注：LightGBM 测试集 AUC 0.808 最优，树模型整体优于线性基线。")

    # 图6-2 阈值优化效果
    fig, ax = plt.subplots()
    x = ["默认阈值 0.50", "代价敏感阈值 0.21"]
    recall = [28.3, 69.6]
    precision = [52.0, 39.0]
    xx = np.arange(2)
    ax.bar(xx - 0.18, recall, width=0.36, color=RISK_COLORS["高危"], label="召回率")
    ax.bar(xx + 0.18, precision, width=0.36, color=PALETTE["primary"], label="精确率")
    for xi, (r, p) in enumerate(zip(recall, precision)):
        ax.text(xi - 0.18, r + 1, f"{r:.1f}%", ha="center", fontsize=10)
        ax.text(xi + 0.18, p + 1, f"{p:.1f}%", ha="center", fontsize=10)
    ax.set_xticks(xx, x)
    ax.set_ylabel("比例 (%)")
    ax.set_ylim(0, 85)
    ax.legend()
    fm6.save(fig, ax, title="代价敏感阈值优化前后对比",
            caption="图注：阈值降至 0.21 后召回率 28.3%→69.6%，漏报大幅减少，符合预警业务取向。")

    # 图7-1 SHAP 风险因子 (真实值来自 src/shap_values.py 输出)
    fm7 = FigureManager(chapter=7, out_dir=OUT)
    shap_file = BASE / "reports" / "shap_importance.json"
    shap_imp = json.loads(shap_file.read_text(encoding="utf-8"))
    feats = list(shap_imp.keys())[:8]
    vals = [shap_imp[k] for k in feats]
    fig, ax = plt.subplots()
    bar(feats, vals, ax=ax, horizontal=True,
        xlabel="平均 |SHAP| 值", ylabel="特征", value_fmt="{:.3f}",
        colors=[PALETTE["primary"]] * len(feats))
    fm7.save(fig, ax, title="SHAP 全局特征重要性 Top8",
            caption="图注：历史挂科次数为首要风险因子（0.561），与单因子分析结论互相印证。")


def main():
    df = load()
    st = run_stats(df)
    make_figures(df, st)
    out = BASE / "reports" / "analysis_results.json"
    out.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"G3: {st['g3']}")
    print(f"预警分布: {st['risk']}  高危占比: {st['high_rate']}")
    print(f"failures: {st['failures']}")
    print(f"studytime: {st['studytime']}")
    print(f"absences: {st['absences']}")
    print(f"higher: {st['higher']}")
    print(f"corr_g3: {st['corr_g3']}")
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
