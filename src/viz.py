# -*- coding: utf-8 -*-
"""
viz.py —— 全项目统一可视化模块（配色 / 中文字体 / 图表编号 / 常用图表）

用法:
    from src.viz import PALETTE, FigureManager, hist, bar, corr_heatmap, box, donut, scatter, line

    fm = FigureManager()          # 章节编号从 1 开始, 生成 "图1-1" 这类编号
    fig, ax = plt.subplots()
    ... 绘图 ...
    fm.save(fig, ax, title="各科目平均成绩分布",
            caption="图注：成绩集中分布在 60~80 分区间, 高分段样本较少。")

所有图表统一:
  - 莫兰迪蓝灰配色 (PALETTE)
  - 中文字体 (Windows 自动使用 微软雅黑/黑体)
  - 300dpi 输出, 自动去顶右边框, 统一网格样式
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Optional, Sequence

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# ----------------------------------------------------------------------------
# 1. 配色系统（莫兰迪蓝灰, 与报告配色保持一致）
# ----------------------------------------------------------------------------
PALETTE = {
    "primary":    "#4A6FA5",   # 主色: 莫兰迪蓝
    "accent1":    "#E07A5F",   # 强调1: 陶土红 (高危/负向)
    "accent2":    "#81B29A",   # 强调2: 灰绿 (正常/正向)
    "accent3":    "#E9C46A",   # 强调3: 沙黄 (关注/中性)
    "text":       "#3D3D3D",   # 正文
    "text_light": "#8C8C8C",   # 辅助文字
    "grid":       "#D9D9D6",   # 网格线
    "bg":         "#FAFAF8",   # 画布背景
}

# 分类色板: 循环使用, 保证同一张图内颜色互不冲突
CATEGORY_COLORS = [
    PALETTE["primary"], PALETTE["accent1"], PALETTE["accent2"],
    PALETTE["accent3"], "#7A6C9B", "#5B8A9A",
]

# 预警等级专用色板 (正常 / 关注 / 高危)
RISK_COLORS = {
    "正常": PALETTE["accent2"],
    "关注": PALETTE["accent3"],
    "高危": PALETTE["accent1"],
}

# 连续色板 (热力图等)
CMAP = "YlGnBu"

FIGURES_DIR = Path(__file__).resolve().parent.parent / "reports" / "figures"


# ----------------------------------------------------------------------------
# 2. 中文字体设置
# ----------------------------------------------------------------------------
def setup_chinese_font() -> str:
    """配置 matplotlib 中文字体, 返回实际使用的字体名。"""
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
                  "Source Han Sans SC", "PingFang SC"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False   # 解决负号显示问题
    return plt.rcParams["font.sans-serif"][0]


# ----------------------------------------------------------------------------
# 3. 全局样式
# ----------------------------------------------------------------------------
def apply_style() -> None:
    """应用全项目统一的图表样式, 在任何绘图前调用一次即可。"""
    font = setup_chinese_font()
    plt.rcParams.update({
        # 画布
        "figure.figsize": (9, 5.6),
        "figure.dpi": 100,
        "figure.facecolor": PALETTE["bg"],
        "savefig.facecolor": PALETTE["bg"],
        # 坐标轴
        "axes.facecolor": PALETTE["bg"],
        "axes.edgecolor": PALETTE["grid"],
        "axes.labelcolor": PALETTE["text"],
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlecolor": PALETTE["text"],
        "axes.labelsize": 12,
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.6,
        "grid.alpha": 0.7,
        "axes.axisbelow": True,
        # 刻度 / 图例 / 文字
        "xtick.color": PALETTE["text"],
        "ytick.color": PALETTE["text"],
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "legend.frameon": False,
        "font.size": 11,
        "font.sans-serif": [font],
    })


def tidy(ax, top: bool = False, right: bool = False) -> None:
    """去掉多余边框, 让图表更清爽。"""
    ax.spines["top"].set_visible(top)
    ax.spines["right"].set_visible(right)


# ----------------------------------------------------------------------------
# 4. 图表编号与保存 (FigureManager)
# ----------------------------------------------------------------------------
class FigureManager:
    """自动管理图表编号 (图1-1, 图1-2, 图2-1 ...) 并统一保存。

    参数
    ----
    chapter : int
        当前章节号, 例如报告第 3 章传 3。
    out_dir : Path
        图片输出目录, 默认 reports/figures。
    """

    def __init__(self, chapter: int = 1,
                 out_dir: Path | str = FIGURES_DIR) -> None:
        self.chapter = chapter
        self.counter = itertools.count(1)
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @property
    def next_number(self) -> str:
        return f"图{self.chapter}-{next(self.counter)}"

    def save(self, fig, ax, *, title: str, caption: str = "",
             filename: Optional[str] = None, tight: bool = True) -> str:
        """设置标题 -> 去边框 -> 保存, 返回图表编号字符串。

        caption 会以小字附在图片底部 (也会写入终端输出方便复制到报告)。
        """
        number = self.next_number
        ax.set_title(title)
        tidy(ax)
        if tight:
            fig.tight_layout()

        # 图注绘制在画布底部
        if caption:
            fig.text(0.5, 0.01, caption, ha="center", va="bottom",
                     fontsize=10, color=PALETTE["text_light"])
            fig.subplots_adjust(bottom=0.18)

        fname = filename or f"{number.replace('图', 'fig_')}.png"
        path = self.out_dir / fname
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"[saved] {number} {title} -> {path}")
        return number


# 初始化全局样式
apply_style()


# ----------------------------------------------------------------------------
# 5. 常用图表封装 (统一风格, 开箱即用)
# ----------------------------------------------------------------------------
def _cycle_colors(n: int) -> list:
    return [CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i in range(n)]


def hist(series, *, ax=None, bins: int = 20, color: str = PALETTE["primary"],
         xlabel: str = "", ylabel: str = "频数"):
    """直方图 (适合成绩、学习时长等连续变量分布)。"""
    ax = ax or plt.subplots()[1]
    ax.hist(series.dropna(), bins=bins, color=color, edgecolor="white",
            alpha=0.9)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return ax


def bar(categories: Sequence, values: Sequence, *, ax=None,
        color: str = PALETTE["primary"], horizontal: bool = False,
        xlabel: str = "", ylabel: str = "", value_fmt: str = "{:.0f}",
        colors: Optional[list] = None):
    """柱状图, 自动标注数值。colors 可传入指定的分类色列表 (如 RISK_COLORS)。"""
    ax = ax or plt.subplots()[1]
    colors = colors or _cycle_colors(len(categories))
    if horizontal:
        bars = ax.barh(categories, values, color=colors, height=0.6)
        ax.invert_yaxis()
        for b, v in zip(bars, values):
            ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                    value_fmt.format(v), va="center", ha="left",
                    color=PALETTE["text"], fontsize=10)
    else:
        bars = ax.bar(categories, values, color=colors, width=0.6)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    value_fmt.format(v), va="bottom", ha="center",
                    color=PALETTE["text"], fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x" if horizontal else "y", visible=False)
    return ax


def corr_heatmap(df, *, ax=None, annot: bool = True):
    """相关系数热力图 (输入 DataFrame, 自动计算相关矩阵)。"""
    ax = ax or plt.subplots()[1]
    corr = df.select_dtypes("number").corr()
    im = ax.imshow(corr, cmap=CMAP, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)), corr.columns,
                  rotation=45, ha="right")
    ax.set_yticks(range(len(corr.columns)), corr.columns)
    if annot:
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f"{corr.iat[i, j]:.2f}",
                        ha="center", va="center",
                        fontsize=8, color=PALETTE["text"])
    ax.grid(visible=False)
    plt.colorbar(im, ax=ax, shrink=0.8)
    return ax


def box(df, by: str, value: str, *, ax=None):
    """分组箱线图 (适合"不同班级/科目的成绩分布"对比)。"""
    ax = ax or plt.subplots()[1]
    groups = [g[value].dropna() for _, g in df.groupby(by)]
    labels = [name for name, _ in df.groupby(by)]
    bp = ax.boxplot(groups, tick_labels=labels, patch_artist=True)
    for patch, c in zip(bp["boxes"], _cycle_colors(len(labels))):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    ax.set_xlabel(by)
    ax.set_ylabel(value)
    return ax


def donut(labels: Sequence, values: Sequence, *, ax=None, title: str = "",
          autopct: str = "%1.1f%%"):
    """环形占比图 (适合预警等级占比)。颜色按 RISK_COLORS 自动匹配。"""
    ax = ax or plt.subplots()[1]
    colors = [RISK_COLORS.get(l, CATEGORY_COLORS[i % len(CATEGORY_COLORS)])
              for i, l in enumerate(labels)]
    wedges, _, _ = ax.pie(
        values, labels=labels, colors=colors, autopct=autopct,
        pctdistance=0.78, startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white"),
    )
    ax.grid(visible=False)
    ax.set_title(title)
    return ax


def scatter(x, y, *, ax=None, color: str = PALETTE["primary"],
            xlabel: str = "", ylabel: str = "", alpha: float = 0.7):
    """散点图 (适合相关关系 / 残差分析)。"""
    ax = ax or plt.subplots()[1]
    ax.scatter(x, y, c=color, alpha=alpha, edgecolors="white", linewidths=0.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return ax


def line(x, y, *, ax=None, color: str = PALETTE["primary"],
         xlabel: str = "", ylabel: str = "", label: str = ""):
    """折线图 (适合趋势 / 调参过程曲线)。"""
    ax = ax or plt.subplots()[1]
    ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=4,
            label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if label:
        ax.legend()
    return ax
