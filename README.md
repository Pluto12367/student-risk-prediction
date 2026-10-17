# 基于可解释机器学习的学业预警系统

> 人工智能实训项目（第二阶段：机器学习 / MLOps）—— 表格数据建模 + Optuna 调参 + MLflow 实验追踪 + SHAP 模型解释 + Streamlit 展示系统。

## 项目结构

```
student-risk-prediction/
├── app/                 # Streamlit 展示系统 (加分项)
│   └── app.py
├── configs/
│   └── best.yaml        # 最优模型配置 (调参后回填, 一键复现)
├── data/
│   ├── raw/             # 原始数据 (UCI Student Performance)
│   └── processed/       # 清洗后建模数据
├── notebooks/           # EDA 探索 (可选)
├── reports/
│   └── figures/         # 统一图表输出 (图1-1, 图2-1 ... 自动编号)
├── src/
│   ├── viz.py           # ★ 统一配色 / 中文字体 / 图表编号模块
│   ├── data_quality.py  # 数据质量检查 →《数据质量分析报告》
│   ├── clean.py         # 清洗 + 特征工程
│   ├── train.py         # 建模 + Optuna 调参 + MLflow 追踪
│   └── explain.py       # SHAP 全局/个体解释
└── requirements.txt
```

## 快速开始

```bash
pip install -r requirements.txt

# 1. 数据质量检查 + 清洗 + EDA
python -m src.data_quality
python -m src.clean
python -m src.eda

# 2. 训练 / 复现实验
python -m src.train --baseline                # 4 模型基线对比
python -m src.train --tune --n-trials 40      # Optuna 调参
python -m src.train                           # 用 best.yaml 一键复现

# 3. 模型解释 (SHAP)
python -m src.explain

# 4. 展示系统
streamlit run app/app.py

# 5. 查看实验追踪
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## 核心指标

基线对比（同一 80/20 分层划分，阈值 0.5，随机种子 42）：

| 模型 | AUC | F1 | Precision | Recall |
|---|---|---|---|---|
| LightGBM（基线） | 0.808 | 0.468 | 0.581 | 0.391 |
| XGBoost（基线） | 0.784 | 0.500 | 0.553 | 0.457 |
| 随机森林（基线） | 0.780 | 0.429 | 0.625 | 0.326 |
| 逻辑回归（基线） | 0.770 | 0.457 | 0.667 | 0.348 |

调参与代价敏感阈值（LightGBM + Optuna 40 trials）：

| 配置 | 验证集 AUC | 测试集 AUC | 阈值 | F1 | Precision | Recall |
|---|---|---|---|---|---|---|
| 调参后 @ 默认阈值 0.5 | 0.869 | 0.783 | 0.50 | 0.366 | 0.520 | 0.283 |
| 调参后 @ 代价敏感阈值 | 0.869 | 0.783 | 0.21 | 0.500 | 0.390 | **0.696** |

**结论（口径与报告保持一致）**：
- Optuna 将**验证集** AUC 提升至 0.869；测试集 AUC 在 0.78~0.81 区间小幅波动（小样本下验证/测试存在随机差异，如实呈现）。
- 业务上更看重**不漏报高危学生**：代价敏感阈值（漏报代价 5 倍于误报）把召回率从 28.3% 提升到 69.6%，F1 从 0.37 提升到 0.50，以约 13 个百分点的精确率换取大幅降低漏报，符合"预警宁可多报、不可漏报"的业务取向。
- 最优参数与阈值已回填 `configs/best.yaml`，`python src/train.py` 可一键复现（指标逐位一致）。
- 全部实验记录在 MLflow（`sqlite:///mlflow.db`），查看：`mlflow ui --backend-store-uri sqlite:///mlflow.db`。

## 图表规范

所有图表由 `src/viz.py` 统一管理：莫兰迪蓝灰配色、中文字体（微软雅黑/黑体）、300dpi、自动编号（图{章}-{序号}）并附图注。报告中引用图表时使用其返回的编号。
