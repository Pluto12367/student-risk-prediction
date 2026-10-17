# -*- coding: utf-8 -*-
"""
eda.py —— 探索性数据分析 (产出《数据分析报告》第 2 章素材)

运行: python src/eda.py
输出: reports/figures/fig_2-*.png
"""

import matplotlib.pyplot as plt
import pandas as pd

from src.data import PROCESSED_DIR
from src.viz import (FigureManager, PALETTE, RISK_COLORS, bar, box,
                     corr_heatmap, donut, hist)


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "clean.csv")
    fm = FigureManager(chapter=2)   # 数据分析报告 EDA = 第 2 章

    # 图2-1 预警等级分布 (环形图, 使用风险专用色)
    counts = df["risk_level"].value_counts()
    fig, ax = plt.subplots()
    donut(counts.index.tolist(), counts.values.tolist(), ax=ax)
    fm.save(fig, ax, title="学生预警等级分布",
            caption="图注：高危(期末不及格)学生约占 22%, 关注段约 29%, 预警覆盖对象明确。")

    # 图2-2 学习时间与期末成绩关系 (箱线图, 有序分类保证横轴顺序)
    order = ["<2h", "2-5h", "5-10h", ">10h"]
    df_plot = df.assign(studytime=pd.Categorical(
        df["studytime"].map(dict(zip(range(1, 5), order))),
        categories=order, ordered=True))
    fig, ax = plt.subplots()
    box(df_plot, by="studytime", value="G3", ax=ax)
    fm.save(fig, ax, title="每周学习时间与期末成绩",
            caption="图注：每周学习 5h 以上组的期末成绩中位数(12~13)高于 5h 以下组(11), 学习时间整体正向但边际收益递减。")

    # 图2-3 历史挂科次数与高危率 (柱状图, 直接呼应 SHAP Top1 特征)
    fail_rate = df.groupby("failures")["label"].mean() * 100
    fig, ax = plt.subplots()
    bar([f"{int(i)}次" for i in fail_rate.index], fail_rate.values, ax=ax,
        xlabel="历史挂科次数", ylabel="高危比例 (%)", value_fmt="{:.0f}%",
        colors=[RISK_COLORS["正常"], RISK_COLORS["关注"], RISK_COLORS["高危"],
                PALETTE["accent1"]][:len(fail_rate)])
    fm.save(fig, ax, title="历史挂科次数与高危比例",
            caption="图注：高危比例随挂科次数单调上升(15%→48%→67%→70%), 与 SHAP 中 failures 为首要因子的结论一致。")

    # 图2-4 数值特征相关性热力图
    fig, ax = plt.subplots()
    corr_heatmap(df[["G3", "studytime", "failures", "absences", "goout",
                     "Dalc", "freetime", "health", "parent_edu"]], ax=ax)
    fm.save(fig, ax, title="关键数值特征相关性",
            caption="图注：G3 与 failures 负相关、与 parent_edu 正相关, 特征间无严重多重共线性。")

    print("EDA 图表完成, 已保存至 reports/figures/")


if __name__ == "__main__":
    main()
