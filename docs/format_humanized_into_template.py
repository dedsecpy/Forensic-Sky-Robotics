"""Format E:\\humanized (Texts Only).docx into CSE-AID template layout with figures/tables."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

TEAM = [
    ("BL.AI.U4AID24078", "Aejaz Ahmad Ansari"),
    ("BL.AI.U4AID24047", "Mutyala Jahnavi Sai"),
    ("BL.AI.U4AID24083", "Divyesh Shanmugarajah"),
]

ROOT = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project")
SRC = Path(r"E:\humanized (Texts Only).docx")
TEMPLATE = Path(r"C:\Users\Work\Downloads\Template - Report - CSE-AID.docx")
ASSETS = ROOT / "docs" / "report_assets"
PLOTS = ROOT / "research_results" / "plots"
LOGO = ASSETS / "template_image_1.png"
OUT = ROOT / "docs" / "Forensic_Sky-Robotics_Project_Report_FORMATTED.docx"
OUT_DL = Path(r"C:\Users\Work\Downloads\Forensic_Sky-Robotics_Project_Report_FORMATTED.docx")

A4W = 5.9
A4W_TALL = 5.4


def font(run, size=12, bold=False, italic=False, name="Times New Roman"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def para(doc, text="", *, align="justify", size=12, bold=False, italic=False, first=True, after=8, line=1.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if line == 1.5 else WD_LINE_SPACING.SINGLE
    pf.space_after = Pt(after)
    pf.space_before = Pt(0)
    pf.first_line_indent = Cm(0.75) if (first and align == "justify" and text) else Cm(0)
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    if text:
        r = p.add_run(text)
        font(r, size=size, bold=bold, italic=italic)
    return p


def heading(doc, text, level=1):
    sizes = {0: 16, 1: 14, 2: 13, 3: 12}
    p = para(doc, text, align="center" if level == 0 else "left", size=sizes.get(level, 12), bold=True, first=False, after=10)
    return p


def caption(doc, text):
    return para(doc, text, align="center", size=11, italic=True, first=False, after=12, line=1.0)


def _set_cell_border_none(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        tcBorders.append(el)
    tcPr.append(tcBorders)


def team_table(doc, members=TEAM):
    """Borderless 2-column roll | name block, centered on the title page."""
    t = doc.add_table(rows=len(members), cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    widths = (Inches(2.35), Inches(2.55))
    for i, (roll, name) in enumerate(members):
        for j, text in enumerate((roll, name)):
            cell = t.rows[i].cells[j]
            cell.width = widths[j]
            _set_cell_border_none(cell)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(text)
            font(r, size=12)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)
    return t


def picture(doc, path: Path, width=A4W):
    if not path.exists():
        para(doc, f"[Missing figure: {path.name}]", align="center", italic=True, first=False)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.first_line_indent = Cm(0)
    p.add_run().add_picture(str(path), width=Inches(width))


def table(doc, headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = t.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        font(r, size=10, bold=True)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(val))
            font(r, size=10)
    doc.add_paragraph()
    return t


def load_paras():
    d = Document(str(SRC))
    return [p.text for p in d.paragraphs]


def T(paras, i):
    return (paras[i] or "").strip()


def build():
    paras = load_paras()
    template = Document(str(TEMPLATE))
    doc = Document()
    s0, d0 = template.sections[0], doc.sections[0]
    d0.page_width = s0.page_width
    d0.page_height = s0.page_height
    d0.left_margin = s0.left_margin
    d0.right_margin = s0.right_margin
    d0.top_margin = s0.top_margin
    d0.bottom_margin = s0.bottom_margin

    # ---------- TITLE PAGE (template order) ----------
    para(doc, "", align="center", first=False, after=12)
    # Use humanized title text
    para(doc, T(paras, 0), align="center", size=14, bold=True, first=False, after=10)
    para(doc, T(paras, 1), align="center", size=13, bold=True, first=False, after=10)
    para(doc, T(paras, 2), align="center", size=12, italic=True, first=False, after=8)
    team_table(doc)
    para(doc, T(paras, 7), align="center", size=12, italic=True, first=False, after=6)
    para(doc, T(paras, 8), align="center", size=12, bold=True, first=False, after=8)
    para(doc, T(paras, 9), align="center", size=12, bold=True, italic=True, first=False, after=1)
    para(doc, T(paras, 10), align="center", size=12, first=False, after=1)
    para(doc, T(paras, 11).rstrip(":"), align="center", size=12, first=False, after=1)
    para(doc, T(paras, 12), align="center", size=12, first=False, after=10)
    if LOGO.exists():
        picture(doc, LOGO, 2.8)
    para(doc, "", align="center", first=False, after=4)
    para(doc, T(paras, 15), align="center", size=12, bold=True, first=False, after=1)
    para(doc, T(paras, 16), align="center", size=12, bold=True, first=False, after=1)
    para(doc, T(paras, 17), align="center", size=12, first=False, after=8)
    para(doc, T(paras, 18), align="center", size=12, bold=True, first=False, after=0)
    doc.add_page_break()

    # ---------- ABSTRACT ----------
    heading(doc, "ABSTRACT", 0)
    para(doc, T(paras, 21))
    para(doc, T(paras, 22))
    para(doc, T(paras, 23))
    para(doc, T(paras, 24), first=False, italic=True)
    doc.add_page_break()

    # ---------- TOC / LISTS (cleaned for readability; body keeps user text) ----------
    heading(doc, "TABLE OF CONTENTS", 0)
    toc = [
        "ABSTRACT\ti",
        "LIST OF FIGURES\tii",
        "LIST OF TABLES\tiii",
        "CHAPTER 1 - INTRODUCTION\t1",
        "    1.1 Problem background\t1",
        "    1.2 Motivation\t2",
        "    1.3 Objectives\t2",
        "    1.4 Scope and limitations\t3",
        "    1.5 Organisation of the report\t3",
        "CHAPTER 2 - LITERATURE REVIEW\t4",
        "    2.1 Team Sports Pose Estimation\t4",
        "    2.2 Recognition of action and foul\t5",
        "    2.3 Anticipation and early prediction\t5",
        "    2.4 Planning sports shots with the camera\t6",
        "    2.5 Summary of gaps\t6",
        "CHAPTER 3 - PROPOSED METHODOLOGY\t7",
        "    3.1 System overview\t7",
        "    3.2 Datasets and splits\t8",
        "    3.3 Perception and features\t9",
        "    3.4 Clip classification protocol\t10",
        "    3.5 Continuous forecasting protocol\t11",
        "    3.6 Virtual camera control\t11",
        "    3.7 Software requirements\t12",
        "    3.8 Hardware requirements\t12",
        "CHAPTER 4 - RESULTS AND DISCUSSION\t13",
        "    4.1 High-level design\t13",
        "    4.2 Low-level design\t14",
        "    4.3 Locked CAS-FD results\t15",
        "    4.4 Continuous World Cup results\t17",
        "    4.5 Supporting pose and camera studies\t18",
        "    4.6 Demonstration system\t19",
        "CHAPTER 5 - CONCLUSION\t20",
        "    5.1 Summary of findings\t20",
        "    5.2 Contributions\t20",
        "    5.3 Future work\t21",
        "REFERENCES\t22",
        "APPENDIX A - Locked metric files\t23",
        "APPENDIX B - How to run the demo\t24",
    ]
    for line in toc:
        para(doc, line, align="left", first=False, after=2)
    doc.add_page_break()

    heading(doc, "LIST OF FIGURES", 0)
    figs = [
        "Figure 3.1 System architecture (end-to-end pipeline)",
        "Figure 3.2 Module map (from README)",
        "Figure 4.1 Overview dashboard of locked evaluations",
        "Figure 4.2 CAS-FD train / validation / test clip counts",
        "Figure 4.3 Locked Step-1 versus Step-2 comparison",
        "Figure 4.4 Final soft-ensemble test metrics",
        "Figure 4.5 Precision-recall curve (clip test)",
        "Figure 4.6 ROC curve (clip test)",
        "Figure 4.7 Confusion matrix (clip test)",
        "Figure 4.8 Score distributions (clip test)",
        "Figure 4.9 Prefix sensitivity study",
        "Figure 4.10 Bootstrap confidence intervals",
        "Figure 4.11 Continuous sample-level metrics",
        "Figure 4.12 Continuous event-level metrics",
        "Figure 4.13 Continuous score timeline (ARG-FRA)",
        "Figure 4.14 Pose PCK / coverage on KTH",
        "Figure 4.15 Virtual camera evaluation",
        "Figure 4.16 Anticipation curve pack",
    ]
    for f in figs:
        para(doc, f, align="left", first=False, after=2)
    doc.add_page_break()

    heading(doc, "LIST OF TABLES", 0)
    tabs = [
        "Table 3.1 CAS-FD retained split counts",
        "Table 3.2 Continuous World Cup match splits",
        "Table 3.3 Software stack used in the project",
        "Table 4.1 Locked clip models and cutoffs",
        "Table 4.2 Held-out CAS-FD test comparison",
        "Table 4.3 Final confusion counts (soft-ensemble)",
        "Table 4.4 Continuous sample-level metrics (ARG-FRA)",
        "Table 4.5 Continuous event-level metrics (18 fouls)",
        "Table 4.6 Demo sample clips shipped with the repository",
    ]
    for tline in tabs:
        para(doc, tline, align="left", first=False, after=2)

    # ---------- CHAPTER 1 ----------
    doc.add_page_break()
    heading(doc, "CHAPTER - 1", 0)
    heading(doc, "INTRODUCTION", 0)
    heading(doc, "1.1 Problem background", 2)
    para(doc, T(paras, 100))
    para(doc, T(paras, 101))
    para(doc, T(paras, 102))
    heading(doc, "1.2 Motivation", 2)
    para(doc, T(paras, 104))
    para(doc, T(paras, 105))
    heading(doc, "1.3 Objectives", 2)
    para(doc, T(paras, 107), first=False)
    for i in range(108, 113):
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        # strip leading numbers already in text
        txt = T(paras, i)
        txt = txt.lstrip("0123456789. ").strip()
        r = p.add_run(txt)
        font(r, 12)
    heading(doc, "1.4 Scope and limitations", 2)
    para(doc, T(paras, 114))
    para(doc, T(paras, 115))
    heading(doc, "1.5 Organisation of the report", 2)
    para(doc, T(paras, 117))

    # ---------- CHAPTER 2 ----------
    doc.add_page_break()
    heading(doc, "CHAPTER - 2", 0)
    heading(doc, "LITERATURE REVIEW", 0)
    heading(doc, "2.1 Team Sports Pose Estimation", 2)
    para(doc, T(paras, 122))
    para(doc, T(paras, 123))
    heading(doc, "2.2 Recognition of action and foul", 2)
    para(doc, T(paras, 125))
    para(doc, T(paras, 126))
    heading(doc, "2.3 Anticipation and early prediction", 2)
    para(doc, T(paras, 128))
    para(doc, T(paras, 129))
    heading(doc, "2.4 Planning sports shots with the camera", 2)
    para(doc, T(paras, 131))
    para(doc, T(paras, 132))
    heading(doc, "2.5 Summary of gaps", 2)
    para(doc, T(paras, 134))

    # ---------- CHAPTER 3 ----------
    doc.add_page_break()
    heading(doc, "CHAPTER - 3", 0)
    heading(doc, "PROPOSED METHODOLOGY", 0)
    heading(doc, "3.1 System overview", 2)
    para(doc, T(paras, 139))
    picture(doc, ASSETS / "fig_pipeline.png", 5.6)
    caption(doc, "Figure 3.1 System architecture: end-to-end pipeline")
    para(doc, T(paras, 142), first=False)
    picture(doc, ASSETS / "fig_modules.png", A4W)
    caption(doc, "Figure 3.2 Module map (Mermaid, from README.md)")
    para(doc, T(paras, 145), first=False)

    heading(doc, "3.2 Datasets and splits", 2)
    para(doc, T(paras, 147))
    table(
        doc,
        ["Split", "Clips", "Foul", "Dive"],
        [
            ["Train", "351", "151", "200"],
            ["Validation", "98", "48", "50"],
            ["Test (held-out)", "95", "45", "50"],
            ["Total retained", "544", "-", "-"],
            ["Raw processed", "600", "-", "-"],
        ],
    )
    caption(doc, "Table 3.1 CAS-FD retained split counts")
    table(
        doc,
        ["Role", "Matches"],
        [
            ["Train", "BRA-SUI, ESP-CRC, FRA-AUS, SRB-SUI"],
            ["Validation", "FRA-DEN, CRC-GER"],
            ["Test", "ARG-FRA final (6,375 samples; 47 positives; 18 fouls)"],
        ],
    )
    caption(doc, "Table 3.2 Continuous World Cup match splits")

    heading(doc, "3.3 Perception and features", 2)
    para(doc, T(paras, 163))
    para(doc, T(paras, 164))
    heading(doc, "3.4 Clip classification protocol", 2)
    para(doc, T(paras, 166))
    para(doc, T(paras, 167))
    heading(doc, "3.5 Continuous forecasting protocol", 2)
    para(doc, T(paras, 169))
    heading(doc, "3.6 Virtual camera control", 2)
    para(doc, T(paras, 171))
    heading(doc, "3.7 Software requirements", 2)
    table(
        doc,
        ["Component", "Version / note"],
        [
            ["Python", "3.11"],
            ["OpenCV", "opencv-contrib-python 5.x"],
            ["Pose", "YOLO11n-pose ONNX; MediaPipe Pose Landmarker"],
            ["Learning", "scikit-learn, CatBoost, joblib"],
            ["Demo UI", "Tkinter, Pillow"],
            ["Optional", "FFmpeg for incident.mp4 export"],
            ["OS for GUI", "Windows (Launch Demo.cmd)"],
        ],
    )
    caption(doc, "Table 3.3 Software stack used in the project")
    heading(doc, "3.8 Hardware requirements", 2)
    para(doc, T(paras, 184))

    # ---------- CHAPTER 4 ----------
    doc.add_page_break()
    heading(doc, "CHAPTER - 4", 0)
    heading(doc, "RESULTS AND DISCUSSION", 0)
    heading(doc, "4.1 High-level design", 2)
    para(doc, T(paras, 189))
    picture(doc, PLOTS / "overview_dashboard.png", A4W)
    caption(doc, "Figure 4.1 Overview dashboard of locked evaluations")
    para(doc, T(paras, 192), first=False)

    heading(doc, "4.2 Low-level design", 2)
    para(doc, T(paras, 194))
    para(doc, T(paras, 195))
    picture(doc, PLOTS / "clip_split_counts.png", 5.4)
    caption(doc, "Figure 4.2 CAS-FD train / validation / test clip counts")

    heading(doc, "4.3 Locked CAS-FD results", 2)
    table(
        doc,
        ["Step", "Model", "Prefix", "Role"],
        [
            ["1", "boosted-deep (CatBoost)", "1.0 s", "Pre-finetune baseline"],
            ["2", "soft-ensemble", "1.0 s", "Locked final classifier"],
        ],
    )
    caption(doc, "Table 4.1 Locked clip models and cutoffs")
    para(doc, T(paras, 204))
    table(
        doc,
        ["Metric", "Step 1 boosted-deep", "Step 2 soft-ensemble (final)"],
        [
            ["Accuracy", "63.2%", "64.2%"],
            ["Balanced accuracy", "63.3%", "64.6%"],
            ["Precision", "60.0%", "60.4%"],
            ["Recall", "66.7%", "71.1%"],
            ["F1", "0.632", "0.653"],
            ["Average precision (AP)", "0.638", "0.650"],
            ["ROC AUC", "0.676", "0.671"],
        ],
    )
    caption(doc, "Table 4.2 Held-out CAS-FD test comparison (95 clips)")
    picture(doc, PLOTS / "locked_clip_comparison.png", 5.5)
    caption(doc, "Figure 4.3 Locked Step-1 versus Step-2 comparison")
    para(doc, T(paras, 217), first=False)

    picture(doc, PLOTS / "clip_test_metrics.png", 5.3)
    caption(doc, "Figure 4.4 Final soft-ensemble test metrics")
    para(doc, T(paras, 220), first=False)

    picture(doc, PLOTS / "clip_pr.png", 5.0)
    caption(doc, "Figure 4.5 Precision-recall curve (clip test)")
    para(doc, T(paras, 223), first=False)

    picture(doc, PLOTS / "clip_roc.png", 5.0)
    caption(doc, "Figure 4.6 ROC curve (clip test)")
    para(doc, T(paras, 226), first=False)

    table(
        doc,
        ["", "Predicted dive / neg", "Predicted foul / pos"],
        [
            ["True dive / neg", "29", "21"],
            ["True foul / pos", "13", "32"],
        ],
    )
    caption(doc, "Table 4.3 Final confusion counts (soft-ensemble)")
    picture(doc, PLOTS / "clip_confusion.png", 4.3)
    caption(doc, "Figure 4.7 Confusion matrix (clip test)")
    para(doc, T(paras, 234), first=False)

    picture(doc, PLOTS / "clip_scores.png", 5.2)
    caption(doc, "Figure 4.8 Score distributions (clip test)")
    para(doc, T(paras, 237), first=False)

    picture(doc, PLOTS / "clip_prefix_sensitivity.png", 5.3)
    caption(doc, "Figure 4.9 Prefix sensitivity study")
    para(doc, T(paras, 240), first=False)

    picture(doc, PLOTS / "clip_bootstrap_ci.png", 5.2)
    caption(doc, "Figure 4.10 Bootstrap confidence intervals")
    para(doc, T(paras, 243), first=False)

    heading(doc, "4.4 Continuous World Cup results", 2)
    para(doc, T(paras, 245))
    table(
        doc,
        ["Metric", "Value"],
        [
            ["Samples / positives", "6375 / 47"],
            ["Accuracy", "98.6% (imbalance-dominated)"],
            ["Balanced accuracy", "0.507"],
            ["Precision / Recall / F1", "0.024 / 0.021 / 0.022"],
            ["AP", "0.0106"],
            ["ROC AUC", "0.510"],
        ],
    )
    caption(doc, "Table 4.4 Continuous sample-level metrics (ARG-FRA)")
    table(
        doc,
        ["Metric", "Value"],
        [
            ["Matched / false / missed", "1 / 14 / 17"],
            ["Event precision", "6.7%"],
            ["Event recall", "5.6%"],
            ["Event F1", "0.061"],
            ["False alerts / min", "0.264"],
            ["Lead (single match)", "1.21 s before event-log time"],
        ],
    )
    caption(doc, "Table 4.5 Continuous event-level metrics (18 fouls)")
    picture(doc, PLOTS / "continuous_sample_metrics.png", 5.2)
    caption(doc, "Figure 4.11 Continuous sample-level metrics")
    picture(doc, PLOTS / "continuous_event_metrics.png", 5.2)
    caption(doc, "Figure 4.12 Continuous event-level metrics")
    para(doc, T(paras, 268), first=False)
    picture(doc, PLOTS / "continuous_score_timeline.png", A4W)
    caption(doc, "Figure 4.13 Continuous score timeline (ARG-FRA)")
    para(doc, T(paras, 271), first=False)

    heading(doc, "4.5 Supporting pose and camera studies", 2)
    picture(doc, PLOTS / "pose_pck_coverage.png", 5.3)
    caption(doc, "Figure 4.14 Pose PCK / coverage on KTH")
    para(doc, T(paras, 275), first=False)
    picture(doc, PLOTS / "camera_evaluation.png", 5.3)
    caption(doc, "Figure 4.15 Virtual camera evaluation")
    para(doc, T(paras, 278), first=False)
    picture(doc, PLOTS / "anticipation_curves.png", 5.6)
    caption(doc, "Figure 4.16 Anticipation curve pack")
    para(doc, T(paras, 281), first=False)

    heading(doc, "4.6 Demonstration system", 2)
    para(doc, T(paras, 283))
    table(
        doc,
        ["Dropdown label", "File"],
        [
            ["World Cup final | Argentina - France", "demo_samples/world_cup_final.mp4"],
            ["CAS-FD foul | challenge 105", "demo_samples/casfd_foul_105.mp4"],
            ["CAS-FD foul | challenge 128", "demo_samples/casfd_foul_128.mp4"],
            ["CAS-FD foul | challenge 107", "demo_samples/casfd_foul_107.mp4"],
            ["CAS-FD dive | challenge 101", "demo_samples/casfd_dive_101.mp4"],
        ],
    )
    caption(doc, "Table 4.6 Demo sample clips shipped with the repository")
    para(doc, T(paras, 292), first=False)

    # ---------- CHAPTER 5 ----------
    doc.add_page_break()
    heading(doc, "CHAPTER - 5", 0)
    heading(doc, "CONCLUSION", 0)
    heading(doc, "5.1 Summary of findings", 2)
    para(doc, T(paras, 297))
    heading(doc, "5.2 Contributions", 2)
    for i in range(299, 303):
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        txt = T(paras, i).lstrip("0123456789. ").strip()
        r = p.add_run(txt)
        font(r, 12)
    heading(doc, "5.3 Future work", 2)
    para(doc, T(paras, 304))

    # ---------- REFERENCES ----------
    doc.add_page_break()
    heading(doc, "REFERENCES", 0)
    for i in range(307, 319):
        txt = T(paras, i)
        if not txt:
            continue
        para(doc, txt, first=False, after=6, size=11)

    # ---------- APPENDICES ----------
    doc.add_page_break()
    heading(doc, "APPENDIX A", 0)
    heading(doc, "Locked metric files", 1)
    para(doc, T(paras, 322))
    doc.add_page_break()
    heading(doc, "APPENDIX B", 0)
    heading(doc, "How to run the demo", 1)
    para(doc, T(paras, 326))
    para(doc, T(paras, 327), first=False, italic=True)

    d0.different_first_page_header_footer = True
    if d0.first_page_footer.paragraphs:
        d0.first_page_footer.paragraphs[0].text = ""
    fp = d0.footer.paragraphs[0] if d0.footer.paragraphs else d0.footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.text = ""
    r = fp.add_run("Dept. of CSE, ASC, Bengaluru  |  23AID301 Computer Vision  |  Forensic Sky-Robotics")
    font(r, 9)

    doc.save(str(OUT))
    try:
        doc.save(str(OUT_DL))
    except Exception as e:
        print("downloads save failed", e)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
