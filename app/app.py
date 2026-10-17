# -*- coding: utf-8 -*-
"""
app.py —— 学业预警展示系统 (Streamlit)

运行: streamlit run app/app.py
功能: 输入学生特征 -> 预测高危概率 -> 三级预警 + SHAP Top3 影响因素 + 干预建议
"""

import json
from pathlib import Path

import pandas as pd
import shap
import streamlit as st
import yaml

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.train import build_model, load_data  # noqa: E402

BASE = Path(__file__).resolve().parent.parent

st.set_page_config(page_title="学业预警系统", page_icon="🎓", layout="wide")


# ---------------------------------------------------------------- 资源加载
@st.cache_resource
def load_assets():
    """训练最优模型并构建 SHAP 解释器 (进程内缓存, 只执行一次)。"""
    with open(BASE / "configs" / "best.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    X_tr, X_te, y_tr, y_te = load_data()
    model = build_model(cfg["model"], cfg["params"], seed=cfg["random_state"])
    model.fit(X_tr, y_tr)
    booster = model.named_steps["model"] if hasattr(model, "named_steps") else model
    explainer = shap.TreeExplainer(booster)
    return cfg, model, explainer, X_tr.columns.tolist()


@st.cache_data
def load_shap_top():
    f = BASE / "reports" / "shap_importance.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


# 中文字段名 -> 建模列名映射说明
INTERVENTION = {
    "failures": ("历史挂科次数多", "安排一对一补弱辅导，制定重修/补强计划"),
    "absences": ("缺勤次数偏高", "家校联动核查缺勤原因，跟踪出勤改善"),
    "higher_yes": ("缺少升学意愿", "开展生涯规划与动机访谈，树立阶段目标"),
    "studytime": ("每周学习时间不足", "制定学习计划，保障自习时间"),
    "goout": ("外出频率偏高", "沟通时间管理，减少无效外出"),
    "Dalc": ("工作日饮酒偏多", "健康教育与家校沟通"),
    "Walc": ("周末饮酒偏多", "健康教育与家校沟通"),
    "paid_yes": ("未参加付费补习", "评估是否需要补习资源支持"),
    "famsup_yes": ("缺少家庭学业支持", "加强家校联系，引导家庭监督"),
    "schoolsup_yes": ("缺少学校额外支持", "申请学校辅导资源"),
    "Fedu": ("父亲受教育程度偏低", "提供家庭教育方法指导"),
    "Medu": ("母亲受教育程度偏低", "提供家庭教育方法指导"),
    "internet_yes": ("家中无网络", "协调校内学习资源使用"),
    "traveltime": ("通勤时间长", "关注作息安排，减少通勤损耗"),
    "romantic_yes": ("恋爱关系影响", "轻度提醒时间分配"),
    "freetime": ("空闲时间偏多", "引导课余时间投入学习"),
    "course_por": ("课程差异", "按课程难度调整学习策略"),
    "school_MS": ("学校因素", "关注校内教学资源差异"),
}


def build_input_frame(raw: dict, feature_cols) -> pd.DataFrame:
    """由原始输入构造与训练一致的特征向量 (含派生字段与独热编码)。"""
    row = {
        "age": raw["age"], "Medu": raw["Medu"], "Fedu": raw["Fedu"],
        "traveltime": raw["traveltime"], "studytime": raw["studytime"],
        "failures": raw["failures"], "famrel": raw["famrel"],
        "freetime": raw["freetime"], "goout": raw["goout"],
        "Dalc": raw["Dalc"], "Walc": raw["Walc"], "health": raw["health"],
        "absences": raw["absences"],
        # 派生字段 (与 src/clean.py 一致)
        "parent_edu": raw["Medu"] + raw["Fedu"],
        "alcohol": (raw["Dalc"] + raw["Walc"]) / 2,
        "support": int(raw["schoolsup"] == "yes") + int(raw["famsup"] == "yes"),
        "study_leisure": raw["studytime"] / (raw["freetime"] + 1),
    }
    # 独热编码 (drop_first=True 口径)
    onehot = {
        "school_MS": int(raw["school"] == "MS"),
        "sex_M": int(raw["sex"] == "M"),
        "address_U": int(raw["address"] == "U"),
        "famsize_LE3": int(raw["famsize"] == "LE3"),
        "Pstatus_T": int(raw["Pstatus"] == "T"),
        "guardian_mother": int(raw["guardian"] == "mother"),
        "guardian_other": int(raw["guardian"] == "other"),
        "schoolsup_yes": int(raw["schoolsup"] == "yes"),
        "famsup_yes": int(raw["famsup"] == "yes"),
        "paid_yes": int(raw["paid"] == "yes"),
        "activities_yes": int(raw["activities"] == "yes"),
        "nursery_yes": int(raw["nursery"] == "yes"),
        "higher_yes": int(raw["higher"] == "yes"),
        "internet_yes": int(raw["internet"] == "yes"),
        "romantic_yes": int(raw["romantic"] == "yes"),
        "course_por": int(raw["course"] == "por"),
    }
    for job, prefix in ((raw["Mjob"], "Mjob"), (raw["Fjob"], "Fjob")):
        for cand in ["health", "other", "services", "teacher"]:
            onehot[f"{prefix}_{cand}"] = int(job == cand)
    for cand in ["home", "other", "reputation"]:
        onehot[f"reason_{cand}"] = int(raw["reason"] == cand)
    row.update(onehot)

    df = pd.DataFrame([row])
    for c in feature_cols:          # 对齐训练列, 缺失补 0
        if c not in df.columns:
            df[c] = 0
    return df[feature_cols]


# ---------------------------------------------------------------- 界面
st.title("🎓 基于可解释机器学习的学业预警系统")
st.caption("输入学生特征 → 预测高危概率 → 三级预警 + Top3 影响因素 + 干预建议（LightGBM + SHAP）")

cfg, model, explainer, feature_cols = load_assets()
thr_high = cfg["risk_threshold"]["high"]
thr_watch = cfg["risk_threshold"]["watch"]

with st.sidebar:
    st.header("📝 学生特征")
    st.subheader("学业历史")
    failures = st.slider("历史挂科次数", 0, 3, 0)
    absences = st.slider("缺勤次数（学年累计）", 0, 93, 5)
    studytime = st.select_slider("每周学习时间", options=[1, 2, 3, 4],
                                 value=2,
                                 format_func=lambda x: {1: "<2h", 2: "2-5h", 3: "5-10h", 4: ">10h"}[x])
    traveltime = st.slider("上学通勤时间 (1=<15min ~ 4=>1h)", 1, 4, 1)

    st.subheader("家庭背景")
    Medu = st.slider("母亲受教育程度 (0=无 ~ 4=高等教育)", 0, 4, 2)
    Fedu = st.slider("父亲受教育程度 (0=无 ~ 4=高等教育)", 0, 4, 2)
    famsize = st.selectbox("家庭规模", ["GT3", "LE3"], format_func=lambda x: ">3人" if x == "GT3" else "≤3人")
    Pstatus = st.selectbox("父母同住状态", ["T", "A"], format_func=lambda x: "同住" if x == "T" else "分居")
    guardian = st.selectbox("监护人", ["mother", "father", "other"],
                            format_func=lambda x: {"mother": "母亲", "father": "父亲", "other": "其他"}[x])
    internet = st.selectbox("家中网络", ["yes", "no"], format_func=lambda x: "有" if x == "yes" else "无")

    st.subheader("行为与心理")
    goout = st.slider("外出频率 (1=很少 ~ 5=很高)", 1, 5, 3)
    Dalc = st.slider("工作日饮酒 (1=很低 ~ 5=很高)", 1, 5, 1)
    Walc = st.slider("周末饮酒 (1=很低 ~ 5=很高)", 1, 5, 2)
    freetime = st.slider("课余空闲时间 (1=很少 ~ 5=很多)", 1, 5, 3)
    health = st.slider("健康状况 (1=很差 ~ 5=很好)", 1, 5, 4)
    famrel = st.slider("家庭关系 (1=很差 ~ 5=很好)", 1, 5, 4)
    higher = st.selectbox("是否有升学意愿", ["yes", "no"], format_func=lambda x: "有" if x == "yes" else "无")
    romantic = st.selectbox("恋爱关系", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")

    st.subheader("其他")
    sex = st.selectbox("性别", ["F", "M"], format_func=lambda x: "女" if x == "F" else "男")
    age = st.slider("年龄", 15, 22, 16)
    school = st.selectbox("学校", ["GP", "MS"])
    address = st.selectbox("家庭住址", ["U", "R"], format_func=lambda x: "城区" if x == "U" else "郊区")
    course = st.selectbox("课程", ["mat", "por"], format_func=lambda x: "数学" if x == "mat" else "葡萄牙语")
    reason = st.selectbox("择校原因", ["course", "home", "reputation", "other"],
                          format_func=lambda x: {"course": "课程", "home": "离家近", "reputation": "声誉", "other": "其他"}[x])
    Mjob = st.selectbox("母亲职业", ["at_home", "health", "other", "services", "teacher"],
                        format_func=lambda x: {"at_home": "全职", "health": "医疗", "other": "其他", "services": "服务业", "teacher": "教师"}[x])
    Fjob = st.selectbox("父亲职业", ["at_home", "health", "other", "services", "teacher"],
                        format_func=lambda x: {"at_home": "全职", "health": "医疗", "other": "其他", "services": "服务业", "teacher": "教师"}[x])
    schoolsup = st.selectbox("额外教育支持", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")
    famsup = st.selectbox("家庭教育支持", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")
    paid = st.selectbox("付费补习（本课程）", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")
    activities = st.selectbox("课外活动", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")
    nursery = st.selectbox("上过幼儿园", ["no", "yes"], format_func=lambda x: "有" if x == "yes" else "无")

raw = dict(failures=failures, absences=absences, studytime=studytime,
           traveltime=traveltime, Medu=Medu, Fedu=Fedu, famsize=famsize,
           Pstatus=Pstatus, guardian=guardian, internet=internet, goout=goout,
           Dalc=Dalc, Walc=Walc, freetime=freetime, health=health, famrel=famrel,
           higher=higher, romantic=romantic, sex=sex, age=age, school=school,
           address=address, course=course, reason=reason, Mjob=Mjob, Fjob=Fjob,
           schoolsup=schoolsup, famsup=famsup, paid=paid, activities=activities,
           nursery=nursery)

X = build_input_frame(raw, feature_cols)
proba = float(model.predict_proba(X)[:, 1][0])

# ---------------------------------------------------------------- 预警结果
col1, col2 = st.columns([1, 2])
with col1:
    if proba >= thr_high:
        level, color, advice_level = "🔴 高危", "red", "立即干预：一对一辅导 + 家校沟通 + 生涯访谈"
    elif proba >= thr_watch:
        level, color, advice_level = "🟡 关注", "orange", "重点关注：学习计划制定 + 月度复盘"
    else:
        level, color, advice_level = "🟢 正常", "green", "常规教学，保持跟踪"
    st.subheader("预警等级")
    st.metric("预测结果", level, delta=f"高危概率 {proba:.1%}",
              delta_color="inverse")
    st.progress(min(proba, 1.0))
    st.caption(f"判定阈值：高危 ≥ {thr_high:.2f}（代价敏感，漏报代价 5 倍于误报），关注 ≥ {thr_watch:.2f}")
    st.info(advice_level)

with col2:
    st.subheader("Top 影响因素与干预建议")
    sv = explainer.shap_values(X)
    sv = sv[1] if isinstance(sv, list) else sv
    contrib = pd.Series(sv[0], index=feature_cols).sort_values()
    top_risk = contrib[contrib > 0].tail(3)[::-1]
    top_protect = contrib[contrib < 0].head(2)

    if len(top_risk):
        for feat, val in top_risk.items():
            base = feat
            name, action = INTERVENTION.get(base, (feat, "结合实际情况制定支持措施"))
            st.markdown(f"**⬆ {name}**（SHAP {val:+.3f}）")
            st.caption(f"干预建议：{action}")
    else:
        st.success("未识别到显著风险因子，风险主要来自特征组合。")

    if len(top_protect):
        st.markdown("**保护性因素**")
        for feat, val in top_protect.items():
            name, _ = INTERVENTION.get(feat, (feat, ""))
            st.caption(f"⬇ {name}（SHAP {val:+.3f}）")

st.divider()

# ---------------------------------------------------------------- 全局参考
with st.expander("📊 全局风险因子参考（SHAP Top10）"):
    top = load_shap_top()
    if top:
        df_top = pd.DataFrame({"特征": list(top.keys()), "平均 |SHAP|": list(top.values())})
        st.bar_chart(df_top.set_index("特征"))
        st.caption("数据来源：reports/shap_importance.json，由 python -m src.shap_values 生成")
    else:
        st.warning("未找到 SHAP 重要性文件，请先运行 python -m src.shap_values")

with st.expander("ℹ️ 使用说明与口径"):
    st.markdown("""
- **模型**：LightGBM（Optuna 调参，测试集 AUC 0.808），代价敏感阈值 0.21，召回率 69.6%。
- **口径**：分析单元为"学生-课程"观测；结论基于葡萄牙 2 所公立中学 2005—2006 学年样本，不得外推总体。
- **解释**：SHAP 值表示各特征对"高危概率"的边际贡献，正值推高风险、负值降低风险。
- **免责**：预警结果为辅助参考，最终干预决策需结合教师的实际观察。
""")
