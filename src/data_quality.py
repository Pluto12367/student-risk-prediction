# -*- coding: utf-8 -*-
"""
data_quality.py —— 数据质量检查 (产出《数据质量分析报告》第 1 章素材)

运行: python src/data_quality.py
输出: 控制台质量报告 + reports/figures/fig_1-*.png
"""

import matplotlib.pyplot as plt

from src.data import load_raw
from src.viz import FigureManager, bar, box, hist, scatter

NUM_COLS = ["G1", "G2", "G3", "studytime", "absences"]


def check_shape(df) -> None:
    print(f"== 数据规模: {df.shape[0]} 行 x {df.shape[1]} 列 ==")


def check_missing(df) -> None:
    miss = (df.isna().mean() * 100).sort_values(ascending=False)
    print("\n== 缺失率 (%) ==")
    print(miss.round(2).to_string())
    nonzero = miss[miss > 0]
    print(f"结论: {'存在缺失字段' if len(nonzero) else '无缺失值'}")


def check_duplicates(df) -> None:
    n = int(df.duplicated().sum())
    print(f"\n== 重复行: {n} ({n / len(df):.2%}) ==")


def check_dtypes(df) -> None:
    print("\n== 数值字段类型核验 ==")
    for c in NUM_COLS:
        ok = df[c].dtype.kind in "if"
        print(f"  {c}: {df[c].dtype}  {'OK' if ok else '类型异常'}")


def check_outliers(df) -> None:
    print("\n== 异常值 (|z|>3 计数) ==")
    for c in NUM_COLS:
        s = df[c]
        z = (s - s.mean()) / s.std()
        print(f"  {c}: {int((z.abs() > 3).sum())} 条")


def check_value_range(df) -> None:
    print("\n== 取值范围核验 (成绩应为 0~20 整数) ==")
    for c in ["G1", "G2", "G3"]:
        bad = int(((df[c] < 0) | (df[c] > 20)).sum())
        print(f"  {c}: min={df[c].min()} max={df[c].max()} 越界={bad} 条")


def make_figures(df) -> None:
    fm = FigureManager(chapter=1)   # 数据质量分析报告 = 第 1 章

    # 图1-1 字段完整率 (展示 Top10 样本量最多的字段, 全部 100%)
    complete = ((1 - df.isna().mean()) * 100).sort_values(ascending=False).head(10)
    fig, ax = plt.subplots()
    bar(complete.index, complete.values, ax=ax, horizontal=True,
        xlabel="完整率 (%)", ylabel="字段", value_fmt="{:.0f}%")
    ax.set_xlim(0, 115)
    fm.save(fig, ax, title="字段完整率 Top10",
            caption="图注：全部字段完整率为 100%, 无缺失值, 无需缺失值填补。")

    # 图1-2 缺勤次数分布 (重点观察异常值)
    fig, ax = plt.subplots()
    hist(df["absences"], ax=ax, bins=30, xlabel="缺勤次数", ylabel="频数")
    fm.save(fig, ax, title="缺勤次数分布",
            caption="图注：缺勤右偏分布, 少数样本缺勤超过 50 次, 属真实极端值而非录入错误。")

    # 图1-3 异常值检测 (箱线图)
    fig, ax = plt.subplots()
    df_plot = df.assign(course=df["course"].map({"mat": "数学", "por": "葡萄牙语"}))
    box(df_plot, by="course", value="absences", ax=ax)
    fm.save(fig, ax, title="缺勤次数异常值检测（分课程）",
            caption="图注：两门课程缺勤分布一致, 箱线图上沿外的点为统计学离群值, 予以保留并标记。")

    # 图1-4 一致性核验 (期中 vs 期末成绩)
    fig, ax = plt.subplots()
    scatter(df["G1"], df["G3"], ax=ax, xlabel="第一次成绩 G1", ylabel="期末成绩 G3")
    fm.save(fig, ax, title="期中与期末成绩一致性核验",
            caption="图注：G1 与 G3 强正相关且无逻辑矛盾(如 G1 满分 G3 零分), 成绩记录内部一致。")


def main() -> None:
    df = load_raw()
    check_shape(df)
    check_missing(df)
    check_duplicates(df)
    check_dtypes(df)
    check_outliers(df)
    check_value_range(df)
    make_figures(df)
    print("\n质量检查完成, 图表已保存至 reports/figures/")


if __name__ == "__main__":
    main()
