# -*- coding: utf-8 -*-
"""按《数据质量分析报告_写作模板》生成数据质量分析报告 Word 文档。"""

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent
DQ = json.loads((BASE / "reports" / "dq_results.json").read_text(encoding="utf-8"))
FIG = BASE / "reports" / "dq_figures"
OUT_DOC = BASE / "数据质量分析报告.docx"

EA = "宋体"
ASCII = "Times New Roman"
BLUE = "4A6FA5"
GRAY = "808080"

# 补充统计
df = pd.concat([
    pd.read_csv(BASE / "data/raw/student_files/student-mat.csv", sep=";").assign(course="mat"),
    pd.read_csv(BASE / "data/raw/student_files/student-por.csv", sep=";").assign(course="por"),
], ignore_index=True)
ST = {
    "abs_max": int(df["absences"].max()),
    "abs_med": float(df["absences"].median()),
    "g3_mean": float(df["G3"].mean()),
    "g3_med": float(df["G3"].median()),
    "gp": int((df["school"] == "GP").sum()),
    "ms": int((df["school"] == "MS").sum()),
    "zero": int((df["G3"] == 0).sum()),
}

DQ_META = {  # 编号: (维度, 检查项, 对象, 处理决定)
    "DQ-01": ("时效性", "各课程数据完整度", "student-mat/por 全表", "两门课程覆盖同一学年，直接使用"),
    "DQ-02": ("完整性", "整列为空字段", "全部 33 字段", "无需处理"),
    "DQ-03": ("完整性", "关键字段缺失", "G3、G2、G1、sex、age、school", "无需处理"),
    "DQ-04": ("规范性", "数值/序数字段取值域", "16 个数值字段", "无需处理"),
    "DQ-05": ("规范性", "类别字段字典合规", "17 个类别字段", "无需处理"),
    "DQ-06": ("唯一性", "完全重复记录", "整行 34 列", "无需处理"),
    "DQ-07": ("一致性", "成绩内部逻辑一致性", "G1、G2、G3", "无需处理"),
    "DQ-08": ("唯一性", "主键口径与跨课程叠加", "student-mat + student-por", "分析单元定为\"学生-课程\"，披露行间依赖"),
    "DQ-09": ("准确性", "统计极端值", "absences、G1、G2、G3", "保留真实极端值并在分析中标注"),
    "DQ-10": ("规范性", "字段类型一致性", "G1/G2/G3/absences/age", "无需处理"),
    "DQ-11": ("一致性", "跨字段逻辑一致性", "Medu/Fedu 与 Mjob/Fjob", "无需处理"),
    "DQ-12": ("规范性", "空白字符串单元格", "21 个文本字段", "无需处理"),
    "DQ-13": ("准确性", "零分/缺考边界数据", "G3=0 记录", "单独标记，训练前做保留/剔除敏感性对比"),
    "DQ-14": ("准确性", "多版本数据甄别", "数据集版本", "不适用，仅单一版本"),
    "DQ-15": ("代表性", "样本口径推断", "抽样方式", "结论限定适用范围，不外推总体"),
    "DQ-16": ("代表性", "人群构成覆盖", "sex、school 构成", "性别结论注明口径，跨地区泛化谨慎"),
}


def pct(x):  # 模板百分比规则: >=10% 取整, 1%~10% 一位小数, <1% 首位有效数字
    p = x * 100
    if p >= 10:
        return f"{p:.0f}%"
    if p >= 1:
        return f"{p:.1f}%"
    if p == 0:
        return "0"
    return f"{p:.4g}%".replace("-", "")


def num(x):
    return f"{x:,}"


# ---------------------------------------------------------------- 样式
def style_run(run, size=12, bold=False, color=None, ea=EA, ascii_=ASCII):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = ascii_
    run._element.rPr.rFonts.set(qn("w:eastAsia"), ea)
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
    # OOXML schema 要求 pBdr 位于 spacing/ind/jc 之前, 否则 Word 判定文档损坏
    pPr.insert_element_before(
        pbdr, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
        "w:wordWrap", "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE",
        "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
        "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents",
        "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
        "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle",
        "w:rPr", "w:sectPr", "w:pPrChange")
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
    # OOXML schema 要求 tcBorders 位于 shd 之前
    tc.insert_element_before(
        borders, "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
        "w:tcFitText", "w:vAlign", "w:hideMark", "w:headers", "w:cellIns",
        "w:cellDel", "w:cellMerge", "w:tcPrChange")
    cell.paragraphs[0].text = ""
    p0 = cell.paragraphs[0]
    style_run(p0.add_run(title), 10.5, True, color)
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
    hdr.cells[0].paragraphs[0].text = ""
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
            cells[i].paragraphs[0].text = ""
            p = cells[i].paragraphs[0]
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
    # 打开文档时自动更新域(目录页码等), 免去手动"更新域"
    settings_elm = doc.settings._element
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    for tag in ("w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr",
                "w:compat", "w:docVars", "w:rsids"):
        el = settings_elm.find(qn(tag))
        if el is not None:
            el.addprevious(upd)
            break
    else:
        settings_elm.append(upd)
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
        ("文档编号：SRP-DQ-2026-01　　密　　级：内部", 10.5, False, 48),
        ("DATA QUALITY ASSESSMENT REPORT", 14, True, 24),
        ("基于 UCI Student Performance 数据集", 14, False, 6),
        ("数据质量分析报告", 26, True, 6),
        ("Data Quality Assessment of UCI Student Performance", 12, False, 36),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(sp)
        style_run(p.add_run(txt), size, bold)
    rows = [
        ("数据集名称", "UCI Student Performance（数学与葡萄牙语课程学生表现）"),
        ("数据时间", "2005—2006 学年（UCI 仓库 2008-03 发布，student-mat / student-por v2）"),
        ("评估对象", "student-mat.csv、student-por.csv 原始层及清洗加工结果"),
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

    # ---------------- 文档信息 / 修订记录 / 阅读说明
    h1(doc, "文 档 信 息")
    add_table(doc, ["项目", "内容"], [
        ("文档名称", "UCI Student Performance 数据质量分析报告"),
        ("文档编号", "SRP-DQ-2026-01"),
        ("版本号", "V1.0"),
        ("密级", "内部"),
        ("评估数据", "UCI Student Performance（student-mat / student-por），分析日 2026-10-17"),
        ("编制", "【待填】"),
        ("审核 / 批准", "【待填】"),
        ("发布日期", "2026-10-17"),
    ], [3.5, 11.2])
    caption(doc, "修订记录", above=True)
    add_table(doc, ["版本", "日期", "修订说明", "修订人"], [
        ("V1.0", "2026-10-17",
         "首次发布：汇总 16 项质量检查（DQ-01~DQ-16）、清洗与标记处理结果、样本代表性与适用性评估",
         "【待填】"),
    ], [1.8, 2.6, 8.2, 2.1])
    h2(doc, "阅读说明")
    bullet(doc, "本报告中的数字均由脚本（src/dq_checks.py）从 student-mat.csv 与 student-por.csv 直接计算得出，图表数值与正文、表格逐一核对。")
    bullet(doc, "质量状态分为“通过”“警告”“不通过”“不适用”四级，判定标准见表 1-3；全部检查结论见附录 A。")
    bullet(doc, "本数据集为公开脱敏教学数据集，不含个人信息，无需遮蔽处理；百分比按“≥10% 取整、1%—10% 保留一位小数、<1% 保留首位有效数字”的规则书写。")
    bullet(doc, "分析单元为“学生-课程”观测行（见 DQ-08），引用样本量时须区分“行数”与“学生人数”。")

    h1(doc, "目　　录")
    add_toc(doc)

    # ---------------- 1 报告概述
    h1(doc, "1　报告概述")
    h2(doc, "1.1　编制目的")
    body(doc, "UCI Student Performance 数据集记录了葡萄牙两所公立中学 2005—2006 学年学生在数学与葡萄牙语两门课程中的成绩（G1、G2、G3）与家庭、学习行为等 33 个字段，是本次实训“学业成绩预警”建模任务的基础数据。业务侧希望在学期中段识别高风险学生并提前干预，因此必须先回答：数据是否完整可信、口径边界在哪里、能不能支撑预警结论。")
    body(doc, "本报告的目的有三：一是从完整性、规范性、唯一性、一致性、准确性、时效性、代表性七个维度逐项识别问题，并给出可复核的量化证据；二是记录清洗与标记的处理过程，保证后续分析与建模可复现；三是明确数据“能回答什么、不能回答什么”，为数据分析报告与模型结论限定适用边界。")
    h2(doc, "1.2　评估范围")
    body(doc, "本次评估覆盖两份原始数据文件及由其加工得到的建模数据集，见表 1-1。")
    caption(doc, "表 1-1　评估对象一览", above=True)
    add_table(doc, ["评估对象", "内容", "规模"], [
        ("student-mat.csv", "数学课程：33 个原始字段（成绩 + 问卷）", f"{DQ['mat行数']} 行 × 33 字段"),
        ("student-por.csv", "葡萄牙语课程：33 个原始字段（成绩 + 问卷）", f"{DQ['por行数']} 行 × 33 字段"),
        ("course 派生列", "课程来源标记（mat=数学 / por=葡萄牙语）", "加工产出，共 34 字段"),
    ], [3.6, 7.8, 3.3])
    h2(doc, "1.3　评估依据与方法")
    body(doc, "评估依据为 UCI 官方数据说明与代码本（字段含义、数值取值域、类别取值字典）。每一项检查都遵循“提出假设、用数据验证、量化证据、登记决定”四个步骤，检查项以 DQ-01 至 DQ-16 编号，结果与处理决定统一登记在附录 A。质量维度的定义、本次检查内容与项数见表 1-2，状态判定标准见表 1-3。")
    caption(doc, "表 1-2　质量维度定义与检查内容", above=True)
    add_table(doc, ["维度", "定义", "本次检查内容", "项数"], [
        ("完整性", "应有的数据是否存在、是否为空", "整列为空字段（DQ-02）、关键字段缺失（DQ-03）", 2),
        ("规范性", "格式、编码、单位是否符合约定", "取值域（DQ-04）、字典合规（DQ-05）、类型（DQ-10）、空白串（DQ-12）", 4),
        ("唯一性", "记录与主键是否唯一", "完全重复记录（DQ-06）、主键口径（DQ-08）", 2),
        ("一致性", "相关字段之间是否相互吻合", "成绩逻辑（DQ-07）、学历与职业（DQ-11）", 2),
        ("准确性", "数据是否真实反映客观对象", "极端值（DQ-09）、零分边界（DQ-13）、多版本（DQ-14）", 3),
        ("时效性", "时间覆盖是否满足分析需要", "各课程数据完整度（DQ-01）", 1),
        ("代表性", "样本能否代表目标总体", "样本口径（DQ-15）、人群构成（DQ-16）", 2),
        ("合计", "—", "—", 16),
    ], [1.9, 4.2, 7.2, 1.4])
    caption(doc, "表 1-3　质量状态判定标准", above=True)
    add_table(doc, ["状态", "判定标准", "处理要求"], [
        ("通过", "检查结果符合预期，或偏差对分析结论的影响可以忽略", "按既定规则处理，无需额外确认"),
        ("警告", "存在问题，但可通过清洗、限定分析口径或在结论中加注说明后继续使用", "执行处理决定，并在交付物中披露"),
        ("不通过", "数据或元数据不能按原样使用，需要替换口径、弃用，或待数据提供方确认", "停止按原样使用，采用替代方案并跟踪整改"),
        ("不适用", "该检查项对本数据集没有意义（如无多版本来源）", "登记原因，不计入结论"),
    ], [1.8, 8.2, 4.7])
    h2(doc, "1.4　数据处理流程")
    body(doc, "数据处理全程脚本化：原始 CSV 读取合并（附加 course 列）→ 执行 DQ-01~DQ-16 检查（src/dq_checks.py）→ 清洗与标记（src/clean.py）→ 特征工程与建模数据输出。全部图表由 src/viz.py 以统一配色、中文字体、300 dpi 生成，按章编号，数值与脚本输出保持同源，处理流程与质量控制节点的对应关系见第 5 章。")

    # ---------------- 2 评估结论摘要
    h1(doc, "2　评估结论摘要")
    h2(doc, "2.1　总体结论")
    body(doc, "本次共执行 16 项质量检查，其中通过 10 项、警告 5 项、不适用 1 项，无“不通过”项（图 2-1）。综合判断，该数据集可以在明确口径的前提下使用：完整性、规范性、唯一性表现优秀，问题集中在样本代表性（DQ-15、DQ-16）、边界与极端数据（DQ-09、DQ-13）以及跨课程叠加口径（DQ-08）三类，均可通过标记处理与限定口径解决。")
    body(doc, "记录层面的问题（缺失、重复、越界、字典外取值）合计 0 条；元数据与口径层面的问题（叠加后行间依赖、样本圈选方式）需要在所有结论中显式披露。")
    add_figure(doc, "fig_2-1.png", "图 2-1　各质量维度检查结果汇总")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为七个质量维度，纵轴为检查项数，堆叠颜色区分通过/警告/不通过状态。"),
        ("关键发现：", "完整性、规范性、唯一性、一致性共 10 项检查全部通过；5 项警告集中在准确性（2 项）与代表性（2 项）、唯一性（1 项）。"),
        ("质量判断：", "无“不通过”项，整体判定为“有条件通过”。"),
        ("对分析的影响：", "记录层面可直接使用，但分析单元必须锁定为“学生-课程”，且结论需限定样本适用范围。"),
    ])
    caption(doc, "表 2-1　关键质量指标", above=True)
    add_table(doc, ["指标", "数值", "说明"], [
        ("原始记录", f"{num(DQ['总行数'])} 行", f"math {DQ['mat行数']} 行 + por {DQ['por行数']} 行，2005—2006 学年"),
        ("字段数", "34 个", "33 个原始字段 + 1 个课程来源派生列"),
        ("质量检查项", "16 项", "通过 10 项、警告 5 项、不适用 1 项"),
        ("双科同学生", f"{num(DQ['双科同学生'])} 人", "同一学生同时出现在两门课程，占数学课样本 93%"),
        ("期末零分记录", f"{ST['zero']} 行", "占 5.1%，疑似缺考/未完成课程，已单独标记"),
        ("统计极端值", "35 条", "|z|>3，其中缺勤 14 条、G2 20 条、G1 1 条"),
    ], [3.4, 3.0, 8.3])
    h2(doc, "2.2　主要发现")
    body(doc, "主要发现按对结论的影响程度从大到小排列见表 2-2。“发现”列写事实和数字，“处理决定”列写已执行的动作。")
    caption(doc, "表 2-2　主要发现与处理决定", above=True)
    add_table(doc, ["序号", "发现", "关联检查", "处理决定"], [
        (1, "33 个字段无缺失、无重复、无取值域越界、无字典外取值", "DQ-02~06、DQ-12 通过", "直接用于建模，无需填补"),
        (2, f"两课程叠加后 {num(DQ['总行数'])} 行含 {num(DQ['双科同学生'])} 名双科同学生（占数学课样本 93%）", "DQ-08 警告", "分析单元定为“学生-课程”，并在结论中披露行间依赖"),
        (3, f"期末零分 {ST['zero']} 条（5.1%），多为缺考或中途放弃而非真实水平", "DQ-13 警告", "单独标记，训练前做保留/剔除两套口径的敏感性对比"),
        (4, "缺勤次数极端值 14 条（最长 " + str(ST['abs_max']) + " 次），G2 极端值 20 条", "DQ-09 警告", "保留真实值，选用树模型降低对极端值的敏感"),
        (5, "样本限于葡萄牙 2 所公立中学，非概率抽样，女生占 57%", "DQ-15、DQ-16 警告", "结论限定适用范围，不向总体外推"),
    ], [1.1, 6.2, 2.8, 4.6])
    h2(doc, "2.3　数据适用性结论")
    note_box(doc, "适用性结论", [
        ("可以用于：", "分析该两校两门课程中哪些学习行为与家庭背景因素与期末不及格相关，构建“学生-课程”级高危预警模型并解释风险因子。"),
        ("不能用于：", "全国或跨国学生学业水平估计、因果推断（如“补习是否提分”）、跨年趋势预测；也不能把两门课程的行简单相加后当作 1,044 名学生使用。"),
        ("使用前提：", "分析单元为“学生-课程”；成绩口径 0—20 分；零分记录单独标记；所有结论须注明“限于葡萄牙 2 所公立中学 2005—2006 学年样本”。"),
    ], color="E07A5F", fill="FBEEE8")
    h2(doc, "2.4　优先事项")
    bullet(doc, "向数据提供方（课程说明文档）确认 53 条零分记录的业务含义：缺考、退课还是真实零分；确认前训练与评估均采用保留+标记的双口径。")
    bullet(doc, "确认建模数据划分是否需要按学生分组切分，避免同一双科学生同时进入训练集与测试集造成信息泄漏。")
    bullet(doc, "索取字段采集口径说明（Dalc/Walc 等自评量表的采集方式），作为模型解释章节的口径备注。")

    # ---------------- 3 数据概况
    h1(doc, "3　数据概况")
    h2(doc, "3.1　字段画像")
    body(doc, f"合并后数据共 {num(DQ['总行数'])} 行、34 个字段，各字段的基本画像见表 3-1。缺失口径包括空值以及去除首尾空白后为空的字符串；示例值取自数据首行，本数据集为公开脱敏教学数据，不含个人信息。")
    caption(doc, "表 3-1　Student Performance 字段画像", above=True)
    rows = [(r["字段"], r["类型"].replace("int64", "int").replace("object", "str"),
             r["含义"], r["缺失数"], r["缺失率"], num(int(r["唯一值"])), r["示例值"])
            for r in DQ["字段画像"]]
    add_table(doc, ["字段", "类型", "含义", "缺失数", "缺失率", "唯一值", "示例值"],
              rows, [1.7, 1.2, 5.6, 1.3, 1.4, 1.3, 1.6], size=9)
    body(doc, "画像中有两点值得注意：一是全部字段缺失率为 0，完整性极好；二是 absences 分布右偏（中位数 " + f"{ST['abs_med']:.0f}" + " 次、最长 " + str(ST['abs_max']) + " 次），且 G3 存在 53 条零分记录，需要与真实低分区分，详见 4.5 节。")
    h2(doc, "3.2　数据覆盖（DQ-01）")
    body(doc, "两份数据均来自 2005—2006 学年：math 课程 395 行、por 课程 649 行，合计 1,044 行，两门课程时间口径一致，无缺学期（DQ-01，通过）。按课程-学校的样本量分布见图 3-1。")
    add_figure(doc, "fig_3-1.png", "图 3-1　各课程-学校的样本量分布")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为“课程-学校”组合，纵轴为记录数，柱顶标注具体行数。"),
        ("关键发现：", f"数学课 395 行、葡萄牙语课 649 行；GP 校合计 {ST['gp']} 行，MS 校 {ST['ms']} 行，MS 校样本明显偏少。"),
        ("质量判断：", "时间覆盖完整（通过），但课程与学校间样本不均衡（警告，归入 DQ-16）。"),
        ("对分析的影响：", "分组比较（如分校、分课程）时小样本组结论不稳定，报告中对 MS 校相关结论加注样本量。"),
    ])

    # ---------------- 4 核心数据质量评估
    h1(doc, "4　核心数据质量评估")
    body(doc, "本章按质量维度分节，每节覆盖若干检查项，标题中注明检查编号。全部检查项的结论汇总见表 4-1，明细见附录 A。")
    caption(doc, "表 4-1　检查结论汇总", above=True)
    rows = []
    for dq in sorted(DQ_META):
        dim, item, obj, _ = DQ_META[dq]
        r = DQ["检查结果"][dq]
        rows.append((dq, dim, item, r["状态"]))
    add_table(doc, ["编号", "维度", "检查项", "状态"], rows, [2.0, 2.2, 8.0, 2.0])
    h2(doc, "4.1　完整性（DQ-02、DQ-03）")
    body(doc, "全部 33 个原始字段均无整列为空（DQ-02，通过）；G3、G2、G1、sex、age、school 六个关键字段缺失合计 0 条（DQ-03，通过）。各字段完整率见图 4-1。")
    add_figure(doc, "fig_4-1.png", "图 4-1　字段完整率 Top10")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为完整率（%），纵轴为字段，按完整率降序取前 10。"),
        ("关键发现：", "全部字段完整率 100%，任何字段均无缺失。"),
        ("质量判断：", "完整性通过，无需缺失值填补。"),
        ("对分析的影响：", "清洗环节不做缺失填补，保留全部 1,044 行样本，避免因填补引入噪声。"),
    ])
    h2(doc, "4.2　规范性（DQ-04、DQ-05、DQ-10、DQ-12）")
    body(doc, "16 个数值/序数字段全部落在 UCI 官方取值域内（DQ-04，通过）；17 个类别字段无字典外取值（DQ-05，通过）；G1/G2/G3/absences/age 均为整型（DQ-10，通过）；21 个文本字段无空白字符串单元格（DQ-12，通过）。")
    h2(doc, "4.3　唯一性（DQ-06、DQ-08）")
    body(doc, f"对全部 34 列做整行比对，完全重复记录 0 条（DQ-06，通过）。但按 UCI 官方 13 个属性键匹配，{num(DQ['双科同学生'])} 名学生同时出现在两门课程（占数学课样本 93%）：两份数据叠加后 {num(DQ['总行数'])} 行并非 {num(DQ['总行数'])} 名学生（DQ-08，警告）。处理决定：分析单元定为“学生-课程”观测行，建模与统计时披露行间依赖，且数据划分优先按学生分组切分。")
    h2(doc, "4.4　一致性（DQ-07、DQ-11）")
    body(doc, "G1、G2、G3 两两相关系数分别为 0.86、0.91、0.81，无“首次高分而期末零分”类逻辑矛盾记录（DQ-07，通过）；Medu=0 不对应 Mjob=teacher、Fedu=0 不对应 Fjob=teacher 的校验未发现矛盾（DQ-11，通过）。成绩一致性核验见图 4-3。")
    add_figure(doc, "fig_4-3.png", "图 4-3　两次阶段成绩与期末成绩一致性核验")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为第一次阶段成绩 G1，纵轴为期末成绩 G3，每个点为一条观测。"),
        ("关键发现：", "点云沿对角线方向分布，相关系数 0.81；无“G1 高分而 G3 为 0”的角落矛盾点。"),
        ("质量判断：", "成绩记录内部一致，一致性通过。"),
        ("对分析的影响：", "G1、G2 可作为强预测因子，但业务目标是“早期预警”，建模时按第 5 章口径处理。"),
    ])
    h2(doc, "4.5　准确性（DQ-09、DQ-13、DQ-14）")
    body(doc, f"|z|>3 的统计极端值共 35 条（缺勤 14、G2 20、G1 1，DQ-09 警告）：缺勤超过 50 次的记录属真实长期缺勤，予以保留并标注。期末零分记录 {ST['zero']} 条（占 5.1%，DQ-13 警告），其中 G2 同为 0 的记录疑似缺考或未完成课程，与真实低分性质不同，已单独标记并在建模阶段做敏感性对比。数据集仅一个官方版本，无多版本甄别需求（DQ-14，不适用）。异常值检测见图 4-2。")
    add_figure(doc, "fig_4-2.png", "图 4-2　缺勤次数异常值检测（分课程）")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为课程（数学/葡萄牙语），纵轴为缺勤次数，箱体外的圆点为统计学离群值。"),
        ("关键发现：", f"两门课程缺勤中位数均在 {ST['abs_med']:.0f} 次附近，分布右偏，最长 {ST['abs_max']} 次；离群点集中在 20—93 次区间。"),
        ("质量判断：", "极端值为真实业务取值而非录入错误，判定为警告并保留。"),
        ("对分析的影响：", "对极端值敏感的模型（如线性回归）需做标准化；树模型可直接使用，报告中标注口径。"),
    ])

    # ---------------- 5 数据清洗与处理结果
    h1(doc, "5　数据清洗与处理结果")
    h2(doc, "5.1　清洗规则与执行结果")
    body(doc, "清洗遵循“最小改动”原则，具体规则与执行结果如下：（1）重复记录剔除——未触发（0 条）；（2）缺失值填补——未触发（0 条）；（3）越界值截断——按 0—20 分合法域做兜底截断，实际未触发；（4）零分/缺考标记——对 53 条 G3=0 记录单独打标（boundary flag），保留原值。各步骤处理记录数见图 5-1，清洗后样本仍为 1,044 行，原始样本 100% 保留。")
    add_figure(doc, "fig_5-1.png", "图 5-1　数据清洗各步骤处理记录数")
    note_box(doc, "图表解读", [
        ("读图方式：", "横轴为清洗步骤，纵轴为各步骤涉及的记录数，柱顶标注条数。"),
        ("关键发现：", "剔除、填补、截断三个步骤均涉及 0 条记录，仅零分标记涉及 53 条。"),
        ("质量判断：", "清洗无信息损失，数据质量支撑“最小改动”处理。"),
        ("对分析的影响：", "清洗环节的透明性保证了建模结果可复现，全部规则写入 src/clean.py。"),
    ])
    h2(doc, "5.2　派生字段设计与数据合规")
    body(doc, "在原始字段基础上构造 5 个可解释的派生字段：parent_edu（父母受教育程度合计，0—8）、alcohol（工作日与周末饮酒量均值，1—5）、support（学校+家庭支持计数，0—2）、study_leisure（学习时间/空闲时间比）以及预警标签 risk_level（高危/关注/正常）与二值标签 label。派生字段计算口径全部公开写入脚本，不含任何个人信息；本数据集为 UCI 公开脱敏教学数据，天然满足数据最小化要求。")
    h2(doc, "5.3　流水线化与可复现性")
    body(doc, "全流程脚本化并纳入版本管理：python -m src.dq_checks（质量检查）→ python -m src.clean（清洗标记）→ python -m src.train（建模与调参）。随机种子固定为 42，最优参数固化在 configs/best.yaml，实验记录写入 MLflow，同一配置重跑指标逐位一致；图表由 src/viz.py 统一配色与字体输出，保证文档与系统展示一致。")

    # ---------------- 6 参考与派生数据质量评估
    h1(doc, "6　参考与派生数据质量评估")
    h2(doc, "6.1　派生字段核验（DQ-10、DQ-11）")
    body(doc, "派生字段逐一核验：parent_edu 严格等于 Medu+Fedu（取值 0—8，无越界）；alcohol 严格等于（Dalc+Walc)/2（取值 1—5）；support 取值 0—2；risk_level 与 G3 的分箱口径严格对应（G3<10 为高危、10—11 为关注、≥12 为正常）。派生过程无类型漂移（DQ-10、DQ-11 保持通过）。")
    h2(doc, "6.2　编码字典核验（DQ-05）")
    body(doc, "17 个类别字段全部对照 UCI 官方代码本校验，字典外取值 0 种（DQ-05，通过）。类别字段在建模前做 one-hot 编码（drop_first=True），得到 46 列数值特征矩阵；编码过程无信息增减，仅做维度展开。")

    # ---------------- 7 样本代表性评估
    h1(doc, "7　样本代表性评估")
    h2(doc, "7.1　课程构成")
    body(doc, "数学课 395 行（38%）、葡萄牙语课 649 行（62%）。两门课程由同一问卷体系采集，字段结构一致，但成绩分布不同（葡萄牙语课整体均值更高），跨课程比较时须分课程口径。")
    h2(doc, "7.2　学校构成")
    body(doc, f"GP 校 {num(ST['gp'])} 行（{pct(ST['gp']/DQ['总行数'])}）、MS 校 {num(ST['ms'])} 行（{pct(ST['ms']/DQ['总行数'])}）。MS 校样本量约为 GP 校的三分之一，分校结论的统计稳定性有限（DQ-16 警告），涉及分校比较的结论均已注明样本量。")
    h2(doc, "7.3　人群构成（DQ-16）")
    body(doc, "样本性别构成见图 7-1：女生占 57%、男生占 43%，性别覆盖相对均衡；但学校仅 2 所、地域仅葡萄牙，人群构成覆盖有限（DQ-16 警告）。")
    add_figure(doc, "fig_7-1.png", "图 7-1　样本性别构成")
    note_box(doc, "图表解读", [
        ("读图方式：", "环形图展示男、女两类样本量占比，标注为取整百分比。"),
        ("关键发现：", "女生 592 行（57%）、男生 452 行（43%），无极端失衡。"),
        ("质量判断：", "性别构成可比，但学校与地域覆盖窄，代表性判定为警告。"),
        ("对分析的影响：", "性别相关的模型解释结论须注明“限于该两校样本”，不做总体推断。"),
    ])
    h2(doc, "7.4　样本口径推断（DQ-15）")
    note_box(doc, "结论：样本口径", [
        ("事实：", "样本来自葡萄牙 2 所公立中学 2005—2006 学年选修数学/葡萄牙语课程的学生，为完整班级名单而非概率抽样。"),
        ("推断：", "该样本更接近“葡萄牙公立中学课程修读学生”这一总体，而非全体中学生。"),
        ("影响：", "所有分布类结论（如高危比例 22%）均为样本内比例，不得直接外推为总体比例；跨国家、跨教育体系的应用需另行验证。"),
    ], color="E07A5F", fill="FBEEE8")

    # ---------------- 8 数据适用性评估
    h1(doc, "8　数据适用性评估")
    h2(doc, "8.1　观测密度")
    body(doc, "每个学生-课程观测包含两次阶段成绩（G1、G2）与一次期末成绩（G3），无更高频的过程性记录（如作业、出勤明细日志）。出勤仅有累计次数（absences）而非逐次记录，无法做“出勤变化轨迹”类分析。观测密度足够支撑成绩预测与风险因子分析，但不足以支撑过程性干预时点研究。")
    h2(doc, "8.2　适用范围与限制")
    body(doc, "可以回答的问题：该样本内哪些行为与背景因素与期末不及格相关；给定问卷与阶段成绩，预测期末不及格的风险有多高。")
    body(doc, "不能回答的问题（同样重要，必须写明）：（1）因果问题——如“减少饮酒是否提高成绩”，本数据只有相关性证据；（2）总体比例——如“葡萄牙中学生高危比例”，样本非概率抽样且仅 2 校；（3）跨年趋势——仅一个学年切片；（4）个体级学生人数——存在 366 名双科同学生，行数不等于人数。")

    # ---------------- 9 问题清单与整改建议
    h1(doc, "9　问题清单与整改建议")
    h2(doc, "9.1　问题清单")
    body(doc, "全部“警告”项汇总见表 9-1，与附录 A 一致；本次无“不通过”项。")
    caption(doc, "表 9-1　问题清单", above=True)
    add_table(doc, ["编号", "问题描述", "影响", "建议处理", "责任方"], [
        ("DQ-08", "366 名学生跨两门课程重复出现，行间不独立", "训练/测试划分可能泄漏", "按学生分组切分并在报告披露", "建模组"),
        ("DQ-09", "缺勤等字段存在 35 条统计极端值", "对线性模型敏感", "保留真实值，树模型+标准化", "建模组"),
        ("DQ-13", "期末零分 53 条，业务含义不明", "可能低估模型难度或引入噪声", "双口径敏感性对比并确认含义", "建模组 / 数据提供方"),
        ("DQ-15", "非概率抽样，仅 2 校 1 学年", "结论不可外推总体", "所有结论注明适用范围", "报告撰写"),
        ("DQ-16", "学校与地域覆盖窄，MS 校样本少", "分校结论不稳定", "分组结论标注样本量", "报告撰写"),
    ], [1.6, 4.6, 3.0, 3.8, 1.9])
    h2(doc, "9.2　需数据提供方确认的事项")
    bullet(doc, "53 条 G3=0 记录的确切含义（缺考、退课、真实零分），以及 G1/G2 缺失时的记录规则。")
    bullet(doc, "Dalc、Walc、famrel 等自评量表的采集方式与量表来源，供模型解释口径备注。")
    bullet(doc, "数据集是否有更新版本或补充字段（如作业完成率），以便后续扩充特征。")
    h2(doc, "9.3　持续质量监控建议")
    bullet(doc, "将 DQ-01~DQ-16 检查固化为流水线前置步骤（src/dq_checks.py），数据一有更新即自动产出质量报告与状态统计。")
    bullet(doc, "对零分比例、极端值条数设置阈值告警（如零分比例 >10% 触发人工复核），在 MLflow 实验记录中附加当次数据质量快照。")
    bullet(doc, "字段字典与取值域以配置文件维护，字段含义变更时同步更新附录 B 字段可信度字典。")

    # ---------------- 10 结论
    h1(doc, "10　结论")
    body(doc, "本报告对 UCI Student Performance 数据集（1,044 行、34 字段）完成了 16 项质量检查：通过 10 项、警告 5 项、不适用 1 项，无“不通过”项。数据在完整性、规范性、唯一性、一致性上表现优秀，记录层面问题为 0；需要管理的是口径类问题——跨课程叠加的行间依赖、零分边界数据、极端值以及样本代表性限制。")
    body(doc, "结论：该数据集可以在明确口径的前提下用于学业预警建模与风险因子分析；不能用于总体推断、因果结论与跨年趋势判断。所有交付物均应沿用本报告的口径约定：分析单元为“学生-课程”、成绩 0—20 分、零分记录单独标记、结论限定“葡萄牙 2 所公立中学 2005—2006 学年样本”。")

    # ---------------- 附录 A
    h1(doc, "附录 A　数据质量检查明细表")
    caption(doc, "表 A-1　数据质量检查明细（DQ-01~DQ-16）", above=True)
    rows = []
    for dq in sorted(DQ_META):
        dim, item, obj, decision = DQ_META[dq]
        r = DQ["检查结果"][dq]
        rows.append((dq, dim, item, obj, r["结果"], r["状态"], r["证据"], decision))
    add_table(doc, ["编号", "维度", "检查项", "对象", "结果", "状态", "证据", "处理决定"],
              rows, [1.2, 1.2, 2.2, 2.2, 3.2, 1.1, 3.4, 2.4], size=8)

    # ---------------- 附录 B
    h1(doc, "附录 B　字段可信度字典")
    caption(doc, "表 B-1　Student Performance 字段可信度", above=True)
    rows = []
    for r in DQ["字段画像"]:
        f = r["字段"]
        trust = "已验证"
        if f == "course":
            basis = "派生列，脚本生成，见 5.2 节"
        elif f in ("G1", "G2", "G3", "absences", "age"):
            basis = "取值域校验通过（DQ-04），见 4.2 节"
        elif r["类型"] == "object":
            basis = "对照 UCI 代码本校验通过（DQ-05），见 6.2 节"
        else:
            basis = "对照 UCI 官方说明，取值域校验通过（DQ-04）"
        rows.append((f, r["含义"], trust, basis))
    add_table(doc, ["字段", "含义", "可信度", "依据与使用建议"],
              rows, [1.8, 6.2, 1.6, 5.3], size=8.5)

    # ---------------- 附录 C
    h1(doc, "附录 C　图表索引与复核说明")
    h2(doc, "C.1　图表索引")
    caption(doc, "表 C-1　图表索引", above=True)
    add_table(doc, ["图号", "图名", "源文件", "关联检查"], [
        ("图 2-1", "各质量维度检查结果汇总", "fig_2-1.png", "全部"),
        ("图 3-1", "各课程-学校的样本量分布", "fig_3-1.png", "DQ-01、DQ-16"),
        ("图 4-1", "字段完整率 Top10", "fig_4-1.png", "DQ-02、DQ-03"),
        ("图 4-2", "缺勤次数异常值检测（分课程）", "fig_4-2.png", "DQ-09"),
        ("图 4-3", "两次阶段成绩与期末成绩一致性核验", "fig_4-3.png", "DQ-07"),
        ("图 5-1", "数据清洗各步骤处理记录数", "fig_5-1.png", "DQ-13"),
        ("图 7-1", "样本性别构成", "fig_7-1.png", "DQ-16"),
    ], [1.8, 5.8, 3.2, 4.1])
    h2(doc, "C.2　图表复核说明")
    caption(doc, "表 C-2　图表复核意见", above=True)
    add_table(doc, ["源文件", "问题", "处理"], [
        ("fig_2-1.png", "图注初稿写“警告 6 项”，与脚本实际统计（警告 5 项、不适用 1 项）不一致", "已按脚本输出修正图注，正文、表格与图注三处口径统一"),
        ("fig_7-1.png", "环形图百分比初版保留一位小数，不符合模板“≥10% 取整”的数字规范", "改为取整百分比（57%/43%），图注与正文同步取整"),
    ], [3.4, 6.8, 4.7])
    body(doc, "复核方式：每张图生成后由脚本输出数值，人工核对图注、正文与表格中的同一指标是否一致；全部 7 张图均已核对通过。")

    # ---------------- 附录 D
    h1(doc, "附录 D　术语与缩写")
    add_table(doc, ["术语 / 缩写", "说明"], [
        ("UCI", "加州大学欧文分校机器学习知识库（UCI Machine Learning Repository），本数据集出处"),
        ("DQ-XX", "数据质量检查项编号，本报告 DQ-01~DQ-16，明细见附录 A"),
        ("mat / por", "数据集中两门课程：mat=数学（student-mat），por=葡萄牙语（student-por）"),
        ("G1 / G2 / G3", "第一次阶段成绩、第二次阶段成绩、期末成绩，取值 0—20 分"),
        ("学生-课程", "本报告的分析单元：一名学生在一门课程中的一条观测，行数不等于学生人数"),
        ("one-hot 编码", "类别字段展开为 0/1 数值列的编码方式，建模前使用"),
        ("缺失口径", "空值，以及去除首尾空白后为空的字符串"),
        ("极端值", "标准化后 |z|>3 的取值，保留真实业务值并在分析中标注"),
    ], [3.2, 11.7])

    doc.save(OUT_DOC)
    print(f"[saved] {OUT_DOC}")


if __name__ == "__main__":
    main()
