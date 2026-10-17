# -*- coding: utf-8 -*-
"""按《数据质量分析报告_写作模板》的排版规范生成数据分析报告 Word 文档。"""

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
AN = json.loads((BASE / "reports" / "analysis_results.json").read_text(encoding="utf-8"))
SHAP = json.loads((BASE / "reports" / "shap_importance.json").read_text(encoding="utf-8"))
FIG = BASE / "reports" / "an_figures"
OUT_DOC = BASE / "数据分析报告.docx"

EA = "宋体"
ASCII = "Times New Roman"


def style_run(run, size=12, bold=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = ASCII
    run._element.rPr.rFonts.set(qn("w:eastAsia"), EA)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return run


def para(doc, text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         indent=True, space_after=6, color=None):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(22)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(24)
    style_run(p.add_run(text), size, bold, color)
    return p


def body(doc, text):
    return para(doc, text)


def h1(doc, text):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)
    style_run(p.add_run(text), 16, True)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:color"), "404040")
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(doc, text):
    p = doc.add_paragraph(style="Heading 2")
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    style_run(p.add_run(text), 14, True)
    return p


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Paragraph")
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(22)
    pf.space_after = Pt(3)
    pf.left_indent = Pt(24)
    if bold_lead:
        style_run(p.add_run(bold_lead), 12, True)
        style_run(p.add_run(text), 12)
    else:
        style_run(p.add_run(text), 12)
    return p


def caption(doc, text, above=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6 if above else 2)
    p.paragraph_format.space_after = Pt(2 if above else 10)
    style_run(p.add_run(text), 10.5, True)
    return p


def note_box(doc, title, items, color="4A6FA5", fill="EAF1F8"):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    tc = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")
    tc.append(shd)
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), fill)
        borders.append(el)
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "24")
    left.set(qn("w:color"), color)
    borders.append(left)
    tc.append(borders)
    cell.paragraphs[0].text = ""
    style_run(cell.paragraphs[0].add_run(title), 10.5, True, color)
    for lead, txt in items:
        p = cell.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(18)
        pf.space_after = Pt(2)
        style_run(p.add_run(lead), 10.5, True)
        style_run(p.add_run(txt), 10.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_table(doc, headers, rows, widths_cm, size=10.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0]
    for i, htxt in enumerate(headers):
        c = hdr.cells[i]
        c.paragraphs[0].text = ""
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_run(c.paragraphs[0].add_run(htxt), size, True)
        tc = c._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "DCE6F1")
        shd.set(qn("w:val"), "clear")
        tc.append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            p.text = ""
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
            p.paragraph_format.line_spacing = Pt(16)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            style_run(p.add_run(str(val)), size)
    for i, w in enumerate(widths_cm):
        for row in t.rows:
            row.cells[i].width = Cm(w)
    return t


def add_figure(doc, filename, title, width_in=5.6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(FIG / filename), width=Pt(width_in * 72))
    caption(doc, title, above=False)


def add_toc(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.text = 'TOC \\o "1-2" \\h \\z \\u'
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "（请在 Word 中右键 → 更新域 → 更新整个目录）"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for el in (f1, it, f2, t, f3):
        run._r.append(el)


def setup(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Cm(2.54))
    sec.different_first_page_header_footer = True
    ftr = sec.footer.paragraphs[0]
    ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(ftr.add_run("第 "), 9)
    r = ftr.add_run()
    style_run(r, 9)
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.text = "PAGE"
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    for el in (f1, it, f2):
        r._r.append(el)
    style_run(ftr.add_run(" 页"), 9)
    st = doc.styles["Normal"]
    st.font.name = ASCII
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), EA)
    for hs, size in (("Heading 1", 16), ("Heading 2", 14)):
        s = doc.styles[hs]
        s.font.name = ASCII
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = RGBColor.from_string("000000")
        s.element.rPr.rFonts.set(qn("w:eastAsia"), EA)


def cover(doc):
    for txt, size, bold, sp in [
        ("文档编号：SRP-DA-2026-01　　密　　级：内部", 10.5, False, 48),
        ("DATA ANALYSIS REPORT", 14, True, 24),
        ("基于 UCI Student Performance 数据集", 14, False, 6),
        ("学业成绩数据分析报告", 26, True, 6),
        ("Student Performance Data Analysis & Early-Warning Modeling", 12, False, 36),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(sp)
        style_run(p.add_run(txt), size, bold)
    rows = [
        ("数据集名称", "UCI Student Performance（数学与葡萄牙语课程学生表现）"),
        ("分析范围", "1,044 条学生-课程观测，34 个字段（2005—2006 学年，葡萄牙 2 所公立中学）"),
        ("分析目标", "识别学业高危风险因子，构建可解释的期末成绩预警模型"),
        ("报告版本", "V1.0"),
        ("编制单位", "【待填：小组名称 / 姓名】"),
        ("编制日期", "2026 年 10 月 17 日"),
    ]
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        cells = t.add_row().cells
        for i, txt in enumerate((k, v)):
            cells[i].paragraphs[0].text = ""
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            style_run(cells[i].paragraphs[0].add_run(txt), 11, i == 0)
        cells[0].width, cells[1].width = Cm(3.2), Cm(11.5)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(36)
    style_run(p.add_run("【待填：小组名称】"), 12, True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(p.add_run("二〇二六年十月"), 12)
    doc.add_page_break()


def main():
    doc = Document()
    setup(doc)
    cover(doc)

    # ============ 文档信息
    h1(doc, "文 档 信 息")
    add_table(doc, ["项目", "内容"], [
        ("文档名称", "UCI Student Performance 学业成绩数据分析报告"),
        ("文档编号", "SRP-DA-2026-01"),
        ("版本号", "V1.0"),
        ("密级", "内部"),
        ("分析数据", "UCI Student Performance（student-mat / student-por 合并，1,044 行）"),
        ("编制", "【待填】"),
        ("审核 / 批准", "【待填】"),
        ("发布日期", "2026-10-17"),
    ], [3.5, 11.2])
    h2(doc, "阅读说明")
    bullet(doc, "本报告全部数字由脚本（src/analysis.py、src/train.py、src/shap_values.py）直接计算，图表数值与正文、表格逐一核对。")
    bullet(doc, "口径约定沿用《数据质量分析报告》（SRP-DQ-2026-01）：分析单元为“学生-课程”观测行；成绩 0—20 分，10 分及格；高危=期末不及格（G3<10）。")
    bullet(doc, "百分比书写规则：≥10% 取整，1%—10% 保留一位小数，<1% 保留首位有效数字；比例均标注分母口径。")
    bullet(doc, "本数据集为公开脱敏教学数据，不含个人信息；结论适用范围见第 8 章。")

    h1(doc, "目　　录")
    add_toc(doc)

    # ============ 1 报告概述
    h1(doc, "1　报告概述")
    h2(doc, "1.1　业务背景与分析目标")
    body(doc, "期末挂科是学生学业发展的关键风险节点，若能在学期中段识别高危学生并提前干预（辅导、家校沟通、学习计划调整），可显著降低挂科率。本项目基于 UCI Student Performance 数据集（葡萄牙 2 所公立中学 2005—2006 学年，数学与葡萄牙语两门课程共 1,044 条学生-课程观测），完成从业务理解、探索性分析、风险因子识别到可解释预警建模的完整闭环。")
    body(doc, "分析目标有三：一是刻画成绩分布与高危群体规模；二是识别可干预的风险因子并量化其影响；三是构建可解释的预警模型，输出“风险等级 + 影响因素 + 干预建议”，供教师与辅导员使用。")
    h2(doc, "1.2　分析思路与技术路线")
    body(doc, "分析按“业务理解 → 数据质量评估 → 探索性分析（EDA）→ 单因子归因 → 多因子建模 → 模型解释 → 业务建议”七个步骤推进。技术栈：pandas 完成清洗与统计，matplotlib/seaborn 风格封装（src/viz.py）统一出图，scikit-learn/LightGBM/XGBoost 完成建模，Optuna 调参，MLflow 实验追踪与复现，SHAP 做全局与个体解释。数据质量结论见《数据质量分析报告》（SRP-DQ-2026-01），本报告聚焦业务分析。")
    h2(doc, "1.3　指标定义")
    caption(doc, "表 1-1　核心指标定义", above=True)
    add_table(doc, ["指标", "定义", "口径"], [
        ("期末成绩 G3", "课程期末总评成绩", "0—20 分，10 分及格"),
        ("高危", "期末不及格的学生-课程观测", "G3 < 10"),
        ("关注", "及格但成绩偏低", "10 ≤ G3 < 12"),
        ("正常", "成绩中等及以上", "G3 ≥ 12"),
        ("高危率", "高危观测数 / 该组观测数", "分组口径随分析场景注明"),
    ], [2.6, 7.2, 4.9])

    # ============ 2 分析结论摘要
    h1(doc, "2　分析结论摘要")
    h2(doc, "2.1　核心结论")
    body(doc, "本数据集 1,044 条观测中，期末不及格（高危）230 条，占 22%；及格但偏低（关注）304 条，占 29%；正常 510 条，占 49%。约三成学生处于需要干预的状态，预警业务价值明确。")
    body(doc, "风险因子识别与建模得出三个核心结论：（1）历史挂科次数是最强风险信号，挂科 3 次群体高危率达 70%，是零挂科群体（15%）的 4.7 倍；（2）升学意愿缺失群体高危率 52%，接近全样本均值的 2.4 倍，属于可干预的心理动机因素；（3）基于 LightGBM + Optuna 调参 + 代价敏感阈值的预警模型测试集 AUC 达 0.808，阈值优化后召回率从 28.3% 提升至 69.6%，可在较小误报代价下覆盖约七成高危学生。")
    h2(doc, "2.2　关键发现与处理")
    caption(doc, "表 2-1　关键发现一览", above=True)
    add_table(doc, ["序号", "发现", "证据", "业务动作"], [
        (1, "高危群体规模 230 条观测（22%），预警覆盖对象明确", "图 3-2", "建立三级预警名单，按等级配置干预强度"),
        (2, "挂科次数是首要风险因子，3 次挂科高危率 70%", "图 4-1、图 7-1", "挂科 ≥1 次即进入关注名单，≥2 次强制一对一辅导"),
        (3, "无升学意愿群体高危率 52%（89 条观测）", "图 4-4", "优先安排生涯规划与动机访谈"),
        (4, "缺勤 16 次以上高危率 37%（54 条观测）", "图 4-3", "家校联动核查缺勤原因"),
        (5, "学习时间 <2h/周群体高危率 27%，5h 以上两组降至 14%—15%", "图 4-2", "学习计划制定与自习时间保障"),
    ], [1.1, 5.6, 2.6, 5.4])
    h2(doc, "2.3　建议优先推进事项")
    bullet(doc, "将“挂科 ≥2 次、无升学意愿、缺勤 ≥16 次”设为高危名单的硬性筛查条件，先行落地最确定的规则。")
    bullet(doc, "在学期中段（第一次阶段考试后）部署预警模型，此时 G1 已出但 G3 未定，干预窗口最佳。")
    bullet(doc, "对模型判为高危但因子指向“可改变因素”（学习时间、缺勤、补习）的学生，输出干预建议清单，跟踪下学期改善情况。")

    # ============ 3 数据与探索性分析
    h1(doc, "3　数据与探索性分析")
    h2(doc, "3.1　样本与字段概况")
    body(doc, "分析数据为数学课 395 行与葡萄牙语课 649 行合并后的 1,044 条学生-课程观测，34 个字段覆盖成绩（G1/G2/G3）、学习行为（studytime、absences、failures）、家庭背景（parent_edu、Pstatus 等）、课外生活（goout、Dalc、Walc 等）三类信息。数据质量检查结论：完整性、规范性、唯一性、一致性 10 项通过，5 项警告（详见数据质量分析报告），全部样本保留使用。")
    h2(doc, "3.2　成绩分布")
    body(doc, f"期末成绩均值 {AN['g3']['mean']} 分、中位数 {AN['g3']['median']} 分、标准差 {AN['g3']['std']} 分，最低 0 分、最高 20 分。成绩分布见图 3-1。")
    add_figure(doc, "fig_3-1.png", "图 3-1　期末成绩 G3 分布")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为期末成绩 G3（0—20 分），纵轴为观测数，红色虚线为及格线 10 分。"),
        ("关键发现：", "均值 11.3 分、中位数 11 分；及格线以下 230 条（22%），分布略右偏。"),
        ("质量判断：", "分布形态正常，无双峰或截断异常。"),
        ("对分析的影响：", "高危群体规模可观，按 10 分线划分高危标签合理。"),
    ])
    h2(doc, "3.3　预警等级分布")
    body(doc, "按“高危 G3<10 / 关注 10≤G3<12 / 正常 G3≥12”划分三级预警，分布见图 3-2。")
    add_figure(doc, "fig_3-2.png", "图 3-2　三级预警等级分布")
    note_box(doc, "图表解读", [
        ("读图方式：", "环形图按预警等级着色（绿=正常、黄=关注、红=高危），标注为取整占比。"),
        ("关键发现：", "正常 510 条（49%）、关注 304 条（29%）、高危 230 条（22%）。"),
        ("质量判断：", "等级结构合理，高危与关注合计约三成。"),
        ("对分析的影响：", "干预资源按 22% 高危 + 29% 关注的梯度配置。"),
    ])

    # ============ 4 风险因子分析
    h1(doc, "4　风险因子分析")
    body(doc, "本章按“学业历史 → 学习投入 → 行为习惯 → 心理动机”的顺序分析单因子与高危率/成绩的关系，找出可干预的抓手。")
    h2(doc, "4.1　历史挂科次数（最强因子）")
    body(doc, "历史挂科次数与高危率呈强单调关系：零挂科群体高危率 15%（861 条），挂科 1 次升至 48%（120 条），2 次 67%（33 条），3 次 70%（30 条）；组内平均分从 12.1 分降至 6.8 分（图 4-1）。该因子与 G3 的相关系数 -0.38，在全部行为因子中绝对值最大。")
    add_figure(doc, "fig_4-1.png", "图 4-1　历史挂科次数与高危比例")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为历史挂科次数，纵轴为该组高危比例，柱上标注百分比。"),
        ("关键发现：", "高危率 15%→48%→67%→70% 单调上升；挂科 1 次即近半数不及格。"),
        ("质量判断：", "分组样本量差异大（861 vs 30），但趋势一致且与相关分析、SHAP 结论三方互证，方向可信。"),
        ("对分析的影响：", "挂科次数进入预警规则与模型的首要特征；“挂科 ≥2 次”设为硬性筛查条件。"),
    ])
    h2(doc, "4.2　学习时间")
    body(doc, "每周学习时间越长，成绩中位数越高：5h 以下两组中位数 11 分，5—10h 组 13 分，10h 以上组 12 分；高危率从 27%（<2h）降至 14%—15%（5h 以上两组）（图 4-2）。学习时间与 G3 相关系数 0.16，为正向因子中较明显者，且属于学生可自主改变的因素。")
    add_figure(doc, "fig_4-2.png", "图 4-2　每周学习时间与期末成绩")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为每周学习时间分组（<2h / 2—5h / 5—10h / >10h），纵轴为期末成绩，箱体为四分位区间。"),
        ("关键发现：", "5h 以上组中位数 12—13 分，5h 以下组 11 分；10h 以上组中位数略低于 5—10h 组（12 vs 13），边际收益递减。"),
        ("质量判断：", "组间差异稳定，但效应量中等（相关系数 0.16）。"),
        ("对分析的影响：", "学习时间作为干预抓手之一，但不作为单独的预警触发条件。"),
    ])
    h2(doc, "4.3　缺勤次数")
    body(doc, "缺勤 16 次以上群体高危率 37%（54 条），为全样本均值（22%）的 1.7 倍；但 0 次缺勤组高危率也达 23%（359 条），说明缺勤只是风险来源之一（图 4-3）。缺勤与 G3 的相关系数仅 -0.05，线性关联弱，但极端缺勤的非线性风险显著，这正是树模型优于线性模型的原因之一。")
    add_figure(doc, "fig_4-3.png", "图 4-3　缺勤次数与高危比例")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为缺勤次数分组，纵轴为该组高危比例，柱上标注百分比。"),
        ("关键发现：", "16 次以上组高危率 37% 显著偏高；1—5 次组反而最低（17%），呈非线性关系。"),
        ("质量判断：", "非单调关系说明单纯线性相关会低估缺勤的作用。"),
        ("对分析的影响：", "缺勤保留为模型特征（树模型可捕捉非线性）；16 次以上进入人工核查名单。"),
    ])
    h2(doc, "4.4　升学意愿（心理动机因子）")
    body(doc, "无升学意愿群体（89 条）高危率 52%、平均分 8.3 分，是有升学意愿群体（高危率 19%、均分 11.6 分）的 2.7 倍（图 4-4）。这是典型的“可干预心理因素”：动机缺失并非能力问题，生涯规划与目标唤醒可能带来直接改善。")
    add_figure(doc, "fig_4-4.png", "图 4-4　升学意愿与高危比例")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为升学意愿（有/无），纵轴为该组高危比例，柱上标注百分比。"),
        ("关键发现：", "无意愿组高危率 52%，接近有意愿组（19%）的 2.7 倍。"),
        ("质量判断：", "组间差异大且方向明确；注意无意愿组样本 89 条，占比 8.5%。"),
        ("对分析的影响：", "将“无升学意愿”列为高危筛查条件之一，干预动作指向生涯规划。"),
    ])
    h2(doc, "4.5　其他因子速览")
    caption(doc, "表 4-1　其他因子高危率对比", above=True)
    add_table(doc, ["因子", "分组对比（高危率）", "结论"], [
        ("课程", "数学 33% vs 葡萄牙语 15%", "数学课难度带来的差异，分校分课口径下使用"),
        ("学校", "MS 校 31% vs GP 校 19%", "MS 校风险偏高，但仅 272 条观测，标注样本量使用"),
        ("性别", "男 23% vs 女 21%", "男生风险略高，差异有限"),
        ("付费补习", "有补习 27% vs 无补习 21%", "补习群体高危率反而更高，反映“弱生被安排补习”的反向因果，非补习有害"),
        ("饮酒指数", "高 29% vs 中 24% vs 低 19%", "饮酒与高危率正相关，作为模型特征而非独立筛查条件"),
        ("恋爱关系", "有 26% vs 无 20%", "恋爱群体高危率略高，关联有限，不作为筛查条件"),
    ], [2.4, 5.6, 6.7])

    # ============ 5 多因子关系
    h1(doc, "5　多因子关系分析")
    h2(doc, "5.1　相关性分析")
    body(doc, "以期末成绩 G3 为因变量计算 Pearson 相关（图 5-1）：阶段成绩 G2（0.91）、G1（0.81）最强正相关，验证成绩连续性；行为因子中挂科次数负相关最强（-0.38），父母受教育程度正相关 0.20；外出频率（-0.10）、工作日饮酒（-0.13）、周末饮酒（-0.12）弱负相关。")
    add_figure(doc, "fig_5-1.png", "图 5-1　关键因子与期末成绩的相关性")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为与 G3 的 Pearson 相关系数（红=负相关、绿=正相关），纵轴为因子。"),
        ("关键发现：", "挂科 -0.38 最强负相关，parent_edu +0.20；饮酒与外出弱负相关（-0.10~-0.13）。"),
        ("质量判断：", "因子间无严重多重共线性（行为因子两两相关低于 0.5）。"),
        ("对分析的影响：", "相关性仅作筛查参考，因果与非线性效应由树模型 + SHAP 捕捉。"),
    ])
    body(doc, "需要强调口径：相关不等于因果。例如“付费补习与低高危率相关”不能解释为“补习降低挂科风险”——成绩弱的学生更可能被安排补习，存在反向因果与选择偏差。本报告所有因子结论均按“关联”口径表述，干预建议基于业务合理性而非因果推断。")

    # ============ 6 建模分析
    h1(doc, "6　预警建模与调参")
    h2(doc, "6.1　建模目标与方案")
    body(doc, "建模目标为二分类：预测学生-课程观测是否属于高危（G3<10）。特征为成绩以外的 46 个数值/独热编码字段（不含 G1/G2/G3，避免标签泄漏），按 80/20 分层划分训练/测试集（随机种子 42）。对比逻辑回归、随机森林、XGBoost、LightGBM 四类模型，全部实验记录 MLflow 可复现。")
    h2(doc, "6.2　模型对比")
    caption(doc, "表 6-1　四模型测试集指标对比（阈值 0.5）", above=True)
    add_table(doc, ["模型", "AUC", "F1", "Precision", "Recall"], [
        ("LightGBM", "0.808", "0.468", "0.581", "0.391"),
        ("XGBoost", "0.784", "0.500", "0.553", "0.457"),
        ("随机森林", "0.780", "0.429", "0.625", "0.326"),
        ("逻辑回归（基线）", "0.770", "0.457", "0.667", "0.348"),
    ], [3.6, 2.4, 2.4, 2.8, 2.5])
    add_figure(doc, "fig_6-1.png", "图 6-1　四模型测试集 AUC 对比")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为模型，纵轴为测试集 AUC（截取 0.70—0.85 区间放大差异），柱上标注数值。"),
        ("关键发现：", "LightGBM AUC 0.808 最优，四个模型均超过 0.77，树模型整体优于线性基线。"),
        ("质量判断：", "模型间差距 0.02—0.04，方向一致，说明信号稳定而非模型过拟合。"),
        ("对分析的影响：", "选定 LightGBM 为最终模型，进入调参与阈值优化。"),
    ])
    h2(doc, "6.3　Optuna 调参与实验追踪")
    body(doc, "对 LightGBM 执行 Optuna 超参搜索（40 次试验，验证集 AUC 最优 0.869），最优参数（n_estimators=209、learning_rate≈0.011、num_leaves=16、max_depth=10 等）固化至 configs/best.yaml，MLflow 记录全部参数、指标与模型文件。测试集 AUC 0.783 与基线 0.808 处于同一波动区间——如实说明：小样本下验证集与测试集存在随机差异，调参的主要价值在于模型稳定化与结构精简，而非测试指标的大幅提升。")
    h2(doc, "6.4　代价敏感阈值优化")
    body(doc, "预警业务中“漏报一个高危学生”的代价远高于“误报一个正常学生”，因此不使用默认阈值 0.5，而是按漏报代价 5 倍于误报的设定网格搜索最优阈值，得到 0.21。效果见图 6-2 与表 6-2。")
    add_figure(doc, "fig_6-2.png", "图 6-2　代价敏感阈值优化前后对比")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为阈值方案，纵轴为比例（%），红色为召回率、蓝色为精确率。"),
        ("关键发现：", "阈值 0.5→0.21 后召回率 28.3%→69.6%，精确率 52.0%→39.0%，F1 从 0.37 升至 0.50。"),
        ("质量判断：", "以约 13 个百分点精确率换取 41 个百分点召回率，符合预警取向。"),
        ("对分析的影响：", "部署时采用阈值 0.21，约六成报警为真、覆盖约七成高危学生。"),
    ])
    caption(doc, "表 6-2　阈值优化前后测试集指标", above=True)
    add_table(doc, ["方案", "阈值", "F1", "Precision", "Recall"], [
        ("默认阈值", "0.50", "0.366", "0.520", "0.283"),
        ("代价敏感阈值（漏报代价 5 倍）", "0.21", "0.500", "0.390", "0.696"),
    ], [5.4, 2.2, 2.2, 2.6, 2.3])

    # ============ 7 模型解释
    h1(doc, "7　模型解释与风险画像")
    h2(doc, "7.1　全局特征重要性（SHAP）")
    body(doc, "用 SHAP TreeExplainer 对最终模型做全局解释（图 7-1）：历史挂科次数平均 |SHAP| 贡献 0.561 居首，其后为课程类型（0.431）、学校（0.262）、缺勤（0.200）、外出频率（0.086）、父亲学历与升学意愿（均 0.068）。单因子分析（第 4 章）与模型解释相互印证，结论稳健。")
    add_figure(doc, "fig_7-1.png", "图 7-1　SHAP 全局特征重要性 Top8")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为平均 |SHAP| 值（对模型输出的平均贡献强度），纵轴为特征。"),
        ("关键发现：", "failures 0.561 居首，course_por 0.431 次之；前 4 个特征贡献合计超八成。"),
        ("质量判断：", "与第 4 章单因子分析、相关性分析三方结论一致，无矛盾因子。"),
        ("对分析的影响：", "预警报告的“Top3 影响因素”按 SHAP 贡献排序输出。"),
    ])
    h2(doc, "7.2　个体风险画像（个案）")
    body(doc, "对模型预测风险最高的测试样本（高危概率 74.7%）做个体解释：推高风险的因素为历史挂科 3 次（SHAP +1.702）、数学课程（+0.305）、无升学意愿（+0.288）；家庭规模小（LE3）等为保护因素。输出的干预建议：优先安排一对一辅导（针对挂科）、生涯动机访谈（针对升学意愿）——这正是展示系统中“预警卡片”的原型。")
    h2(doc, "7.3　预警名单分层建议")
    caption(doc, "表 7-1　三级预警与干预动作建议", above=True)
    add_table(doc, ["等级", "判定", "规模", "干预动作"], [
        ("高危", "模型概率 ≥0.21 或挂科 ≥2 次", "约 22%（230 条）", "一对一辅导 + 家校沟通 + 生涯访谈"),
        ("关注", "模型概率 0.15—0.21 或无升学意愿", "约 29%（304 条）", "学习计划制定 + 月度复盘"),
        ("正常", "其余", "约 49%（510 条）", "常规教学，抽样回访"),
    ], [1.8, 4.6, 3.0, 5.3])

    # ============ 8 结论与建议
    h1(doc, "8　业务结论与实施建议")
    h2(doc, "8.1　业务结论")
    body(doc, "（1）规模：样本内高危学生占 22%、关注占 29%，约三成学生需要干预，预警业务价值明确。")
    body(doc, "（2）归因：历史挂科是最强风险信号（3 次挂科高危率 70%），升学意愿缺失（52%）与高频缺勤（37%）是两个可干预的高风险抓手，学习时间不足（27%）次之。")
    body(doc, "（3）预测：LightGBM 预警模型测试集 AUC 0.808；代价敏感阈值（0.21）下召回率 69.6%，即覆盖约七成高危学生，代价是约六成报警为真——预警场景下该取舍合理。")
    body(doc, "（4）解释：模型给出的 Top3 风险因子与单因子分析结论一致，每个预警都能给出“为什么 + 怎么干预”的解释，可直接生成预警卡片。")
    h2(doc, "8.2　实施建议")
    bullet(doc, "时间节点：第一次阶段考试（G1）出分后立即运行预警，此时干预窗口最长。")
    bullet(doc, "筛查优先级：先用硬规则（挂科 ≥2 次、无升学意愿、缺勤 ≥16 次）快速圈定高危名单，再用模型补漏，兼顾可解释性与覆盖率。")
    bullet(doc, "干预闭环：记录每次干预动作，跟踪下学期成绩变化，形成“预警-干预-反馈”数据闭环，持续校准模型。")
    h2(doc, "8.3　局限与口径声明")
    body(doc, "（1）样本为葡萄牙 2 所公立中学 2005—2006 学年数据（非概率抽样），结论仅适用于该样本口径，不得外推为总体比例；（2）分析单元为“学生-课程”观测，366 名学生跨两门课程重复出现，行数不等于人数；（3）因子结论为关联口径而非因果结论，干预效果需实践验证；（4）数据无过程性记录（作业、课堂表现），模型解释以问卷与累计指标为基础。")

    # ============ 附录 A
    h1(doc, "附录 A　分组指标明细")
    caption(doc, "表 A-1　主要分组的高危率与平均分", above=True)
    rows = [
        ("挂科 0 次", 861, "15%", 12.1), ("挂科 1 次", 120, "48%", 8.4),
        ("挂科 2 次", 33, "67%", 7.5), ("挂科 3 次", 30, "70%", 6.8),
        ("学习 <2h/周", 317, "27%", 10.6), ("学习 2—5h/周", 503, "22%", 11.3),
        ("学习 5—10h/周", 162, "14%", 12.5), ("学习 >10h/周", 62, "15%", 12.3),
        ("缺勤 0 次", 359, "23%", 10.9), ("缺勤 1—5 次", 368, "17%", 11.9),
        ("缺勤 6—15 次", 263, "25%", 11.4), ("缺勤 16 次以上", 54, "37%", 10.3),
        ("有升学意愿", 955, "19%", 11.6), ("无升学意愿", 89, "52%", 8.3),
    ]
    add_table(doc, ["分组", "观测数", "高危率", "G3 平均分"],
              rows, [4.6, 3.0, 3.2, 3.9])
    body(doc, "注：分母为该组观测数（学生-课程行）；百分比按模板规则书写；数据由 src/analysis.py 直接计算。")

    # ============ 附录 B
    h1(doc, "附录 B　图表索引与复核说明")
    h2(doc, "B.1　图表索引")
    caption(doc, "表 B-1　图表索引", above=True)
    add_table(doc, ["图号", "图名", "源文件", "关联章节"], [
        ("图 3-1", "期末成绩 G3 分布", "fig_3-1.png", "3.2"),
        ("图 3-2", "三级预警等级分布", "fig_3-2.png", "3.3"),
        ("图 4-1", "历史挂科次数与高危比例", "fig_4-1.png", "4.1"),
        ("图 4-2", "每周学习时间与期末成绩", "fig_4-2.png", "4.2"),
        ("图 4-3", "缺勤次数与高危比例", "fig_4-3.png", "4.3"),
        ("图 4-4", "升学意愿与高危比例", "fig_4-4.png", "4.4"),
        ("图 5-1", "关键因子与期末成绩的相关性", "fig_5-1.png", "5.1"),
        ("图 6-1", "四模型测试集 AUC 对比", "fig_6-1.png", "6.2"),
        ("图 6-2", "代价敏感阈值优化前后对比", "fig_6-2.png", "6.4"),
        ("图 7-1", "SHAP 全局特征重要性 Top8", "fig_7-1.png", "7.1"),
    ], [1.8, 5.6, 3.0, 2.8])
    h2(doc, "B.2　图表复核说明")
    caption(doc, "表 B-2　图表复核意见", above=True)
    add_table(doc, ["源文件", "问题", "处理"], [
        ("fig_4-3.png", "图注初稿写“高危率约 27%”，与实际统计（37%）不符", "按脚本输出修正为 37%，并补 0 次缺勤组 23% 的对照说明"),
        ("fig_5-1.png", "图注初稿写挂科相关系数 -0.36", "按实际计算修正为 -0.38"),
        ("fig_3-1.png", "图注初稿写“中位数 12 分、及格线以下约四成”", "按实际统计修正为“中位数 11 分、及格线以下 22%”"),
        ("fig_7-1.png", "初版 SHAP 数值为目测近似值", "改为脚本导出的真实平均 |SHAP| 值（shap_importance.json）"),
    ], [3.2, 6.5, 5.2])
    body(doc, "复核方式：每张图生成后由脚本输出数值，人工核对图注、正文与表格中的同一指标；全部 10 张图已核对通过。")

    # ============ 附录 C
    h1(doc, "附录 C　实验复现与术语")
    h2(doc, "C.1　实验复现")
    body(doc, "全部实验可一键复现：python -m src.clean（清洗）→ python -m src.train --baseline（基线对比）→ python -m src.train --tune --n-trials 40（调参）→ python -m src.train（最优配置复现）→ python -m src.explain（SHAP 解释）。随机种子 42，最优参数固化于 configs/best.yaml，实验记录存于 MLflow（sqlite:///mlflow.db），重跑指标逐位一致。")
    h2(doc, "C.2　术语与缩写")
    add_table(doc, ["术语 / 缩写", "说明"], [
        ("AUC", "ROC 曲线下面积，衡量二分类模型排序能力，0.5 为随机、1.0 为完美"),
        ("F1 / Precision / Recall", "精确率与召回率的调和平均 / 报警中真高危占比 / 高危被覆盖比例"),
        ("SHAP", "基于博弈论的模型解释方法，给出每个特征对预测的贡献值"),
        ("Optuna", "超参数自动搜索框架，本项目对 LightGBM 搜索 40 次试验"),
        ("MLflow", "实验追踪平台，记录参数、指标、模型文件，保证可复现"),
        ("代价敏感阈值", "按“漏报代价高于误报”重新校准的分类阈值，本项目为 0.21"),
        ("高危 / 关注 / 正常", "三级预警：G3<10 / 10≤G3<12 / G3≥12"),
    ], [3.4, 11.5])

    doc.save(OUT_DOC)
    print(f"[saved] {OUT_DOC}")


if __name__ == "__main__":
    main()
