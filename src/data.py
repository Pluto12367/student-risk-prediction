# -*- coding: utf-8 -*-
"""
data.py —— 原始数据加载 (UCI Student Performance: 数学 + 葡萄牙语两门课)

两份数据字段一致, 叠加后增加 course 列 (mat=数学 / por=葡萄牙语),
共 395 + 649 = 1044 条课程-学生观测。
"""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "data" / "raw" / "student_files"
PROCESSED_DIR = BASE / "data" / "processed"


def load_raw() -> pd.DataFrame:
    """加载并合并两门课的原始数据。"""
    frames = []
    for name, course in [("student-mat.csv", "mat"), ("student-por.csv", "por")]:
        df = pd.read_csv(RAW_DIR / name, sep=";")
        df["course"] = course
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
