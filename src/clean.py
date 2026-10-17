# -*- coding: utf-8 -*-
"""
clean.py —— 数据清洗、特征工程与预警标签生成

运行: python src/clean.py
输出: data/processed/clean.csv

预警等级标签 (依据期末成绩 G3, 满分 20):
    高危  G3 <  10   不及格
    关注  10 <= G3 < 12  低分飘过
    正常  G3 >= 12

建模目标 label: 二值"是否高危" (1=高危), 供模型学习;
risk_level 为三级标签, 供报告分析与展示系统使用。
"""

import pandas as pd

from src.data import PROCESSED_DIR, load_raw

# 分类字段 -> one-hot; 数值/序数字段保留
CAT_COLS = ["school", "sex", "address", "famsize", "Pstatus", "Mjob",
            "Fjob", "reason", "guardian", "schoolsup", "famsup", "paid",
            "activities", "nursery", "higher", "internet", "romantic", "course"]
NUM_COLS = ["age", "Medu", "Fedu", "traveltime", "studytime", "failures",
            "famrel", "freetime", "goout", "Dalc", "Walc", "health", "absences"]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates()
    df = df.dropna()
    # 成绩越界截断到合法区间 (质检显示无越界, 此处兜底)
    for c in ["G1", "G2", "G3"]:
        df[c] = df[c].clip(0, 20)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """构造可解释的行为特征 (不含 G1/G2, 避免泄漏, 实现"早期预警")。"""
    df["parent_edu"] = df["Medu"] + df["Fedu"]              # 父母受教育程度合计
    df["alcohol"] = (df["Dalc"] + df["Walc"]) / 2           # 饮酒指数(工作日/周末均值)
    df["support"] = (df["schoolsup"].eq("yes").astype(int)
                     + df["famsup"].eq("yes").astype(int))  # 学业支持计数
    df["study_leisure"] = df["studytime"] / (df["freetime"] + 1)  # 学习/闲暇比
    return df


def make_label(df: pd.DataFrame) -> pd.DataFrame:
    g3 = df["G3"]
    df["risk_level"] = pd.cut(g3, bins=[-1, 9, 11, 20],
                              labels=["高危", "关注", "正常"])
    df["label"] = (g3 < 10).astype(int)   # 1 = 高危
    return df


def encode(df: pd.DataFrame) -> pd.DataFrame:
    df = pd.get_dummies(df, columns=CAT_COLS, drop_first=True, dtype=int)
    return df


def main() -> None:
    df = load_raw()
    raw_shape = df.shape
    df = clean(df)
    df = add_features(df)
    df = make_label(df)

    # 建模数据: 去掉成绩类列防止泄漏
    model_df = df.drop(columns=["G1", "G2", "G3"])
    model_df = encode(model_df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "clean.csv", index=False)          # 含 risk_level 供分析
    model_df.to_csv(PROCESSED_DIR / "model.csv", index=False)    # 建模专用

    print(f"原始: {raw_shape} -> 清洗后: {df.shape}")
    print("\n== 预警等级分布 ==")
    print(df["risk_level"].value_counts().to_string())
    print(f"\n高危占比: {df['label'].mean():.2%}")
    print(f"[saved] {PROCESSED_DIR / 'clean.csv'}")
    print(f"[saved] {PROCESSED_DIR / 'model.csv'}  shape={model_df.shape}")


if __name__ == "__main__":
    main()
