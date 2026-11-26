"""Build the CSE-AID formatted project report DOCX from locked results and plots."""
from __future__ import annotations

import base64
import urllib.request
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project")
TEMPLATE = Path(r"C:\Users\Work\Downloads\Template - Report - CSE-AID.docx")
OUT = ROOT / "docs" / "Forensic_Sky-Robotics_Project_Report.docx"
OUT_ALT = ROOT / "docs" / "Forensic_Sky-Robotics_Project_Report_final.docx"
ASSETS = ROOT / "docs" / "report_assets"
PLOTS = ROOT / "research_results" / "plots"
LOGO = ASSETS / "template_image_1.png"
ASSETS.mkdir(parents=True, exist_ok=True)

# A4 printable width ~6.1 in with typical template margins
A4_FIG_W = 5.9
A4_FIG_W_TALL = 5.5

TEAM = [
    ("BL.AI.U4AID24078", "Aejaz Ahmad Ansari"),
    ("BL.AI.U4AID24047", "Mutyala Jahnavi Sai"),
    ("BL.AI.U4AID24083", "Divyesh Shanmugarajah"),
]


def set_run_font(run, name="Times New Roman", size=12, bold=False, italic=False):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def set_para(p, *, align="justify", space_after=8, first_line=True, line=1.5):
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE if line == 1.5 else WD_LINE_SPACING.SINGLE
    if line == 1.5:
        pf.line_spacing = 1.5
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    if align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if first_line and align == "justify":
        pf.first_line_indent = Cm(0.75)
    else:
        pf.first_line_indent = Cm(0)


def add_text(doc, text, *, style=None, align="justify", size=12, bold=False, italic=False, first_line=True, space_after=8):
    p = doc.add_paragraph()
    if style:
        try:
            p.style = style
        except Exception:
            pass
    set_para(p, align=align, first_line=first_line and align == "justify", space_after=space_after)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def add_heading_custom(doc, text, level=1):
    p = doc.add_paragraph()
    set_para(p, align="left", first_line=False, space_after=10, line=1.5)
    size = {0: 16, 1: 14, 2: 13, 3: 12}.get(level, 12)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=True)
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    set_para(p, align="center", first_line=False, space_after=12, line=1.0)
    run = p.add_run(text)
    set_run_font(run, size=11, italic=True)
    return p


def add_picture(doc, path: Path, width_in=5.8):
    if not path.exists():
        add_text(doc, f"[Missing figure: {path.name}]", align="center", first_line=False, italic=True)
        return
    p = doc.add_paragraph()
    set_para(p, align="center", first_line=False, space_after=4, line=1.0)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_run_font(run, size=10, bold=True)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(str(val))
            set_run_font(run, size=10)
    doc.add_paragraph()
    return table


def render_mermaid(name: str, diagram: str) -> Path:
    """Render Mermaid to PNG via mermaid.ink (A4-friendly source layouts)."""
    raw = diagram.strip().encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("ascii")
    url = f"https://mermaid.ink/img/{b64}?bgColor=white"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=90).read()
    fp = ASSETS / f"{name}.png"
    fp.write_bytes(data)
    # also keep .mmd source next to the figure for the report archive
    (ASSETS / f"{name}.mmd").write_text(diagram.strip() + "\n", encoding="utf-8")
    return fp


def make_diagrams():
    # Exact system diagrams from README.md (A4-scaled when inserted).
    pipeline = """
flowchart TB
  subgraph Input["Input"]
    V["Match clip / broadcast<br/>demo_samples/*.mp4"]
  end

  subgraph Perception["Perception"]
    DET["YOLO11n-pose detection"]
    TRK["Multi-player tracker<br/>+ shot-cut reset"]
    FEAT["PairHistory features<br/>27-D pairs → 81-D scene"]
    MP["MediaPipe 3D pose<br/>display landmarks"]
  end

  subgraph Anticipation["Anticipation"]
    CTRL["VideoController"]
    CLIP["Clip track<br/>soft-ensemble / boosted-deep"]
    CONT["Continuous track<br/>L2 logistic regression"]
    ALARM["Causal Alarm<br/>threshold + refractory"]
    HOLD["TargetHold<br/>threatened pair lock"]
  end

  subgraph Camera["Virtual skycam"]
    PLAN["Viewpoint planner<br/>clear sightline + motion limits"]
    SIM["3D pitch / path render"]
  end

  subgraph Delivery["Demo delivery"]
    AN["analyze.py<br/>replay.mp4 + telemetry.jsonl"]
    UI["demo.py GUI<br/>broadcast | skycam"]
    HUD["Ops dashboard<br/>risk · warning · camera map"]
    OUT["runs/ summary + incident clip"]
  end

  V --> DET --> TRK --> FEAT
  TRK --> MP
  FEAT --> CTRL
  CTRL --> CLIP
  CTRL --> CONT
  CLIP --> ALARM
  CONT --> ALARM
  ALARM --> HOLD
  HOLD --> PLAN --> SIM
  TRK --> AN
  MP --> AN
  SIM --> AN
  ALARM --> AN
  AN --> UI
  AN --> HUD
  AN --> OUT
  UI --- HUD
"""
    modules = """
flowchart LR
  subgraph Core["core/"]
    vision["vision · video_pose"]
    anticipation["anticipation · in_play"]
    camera["camera"]
    learning["learning"]
  end

  subgraph Train["training/"]
    fit["fit_video.py"]
    match["match_training.py"]
  end

  subgraph Eval["evaluation/"]
    analyze["analyze.py"]
    demo["demo.py + dashboard.py"]
    plots["plot_results.py"]
  end

  subgraph Artifacts["Artifacts"]
    models["models/*.joblib"]
    results["research_results/"]
    samples["demo_samples/"]
  end

  vision --> anticipation
  anticipation --> fit
  anticipation --> match
  fit --> models
  match --> models
  models --> analyze
  camera --> analyze
  vision --> analyze
  analyze --> demo
  samples --> demo
  fit --> plots
  match --> plots
  plots --> results
"""
    # fig_pipeline.png is supplied externally (square pipeline figure); do not overwrite.
    render_mermaid("fig_modules", modules)
    _ = pipeline  # kept for archive / reference only


def copy_section_geometry(src: Document, dst: Document):
    # Keep first section page size/margins close to template.
    s0, d0 = src.sections[0], dst.sections[0]
    d0.page_width = s0.page_width
    d0.page_height = s0.page_height
    d0.left_margin = s0.left_margin
    d0.right_margin = s0.right_margin
    d0.top_margin = s0.top_margin
    d0.bottom_margin = s0.bottom_margin


def build():
    make_diagrams()
    template = Document(str(TEMPLATE))
    doc = Document()
    copy_section_geometry(template, doc)

    # ---- Title page: match CSE-AID template order (logo under degree block) ----
    if not LOGO.exists():
        tdoc = Document(str(TEMPLATE))
        for rel in tdoc.part.rels.values():
            if "image" in rel.reltype:
                LOGO.write_bytes(rel.target_part.blob)
                break

    add_text(doc, "", align="center", first_line=False, space_after=18)
    add_text(
        doc,
        "Forensic Sky-Robotics: Pre-Cognitive Aerial Camera Repositioning Driven by the Spatiotemporal Prediction of Infraction Precursors",
        align="center",
        size=14,
        bold=True,
        first_line=False,
        space_after=10,
    )
    add_text(doc, "A PROJECT REPORT", align="center", size=13, bold=True, first_line=False, space_after=10)
    add_text(doc, "Submitted by", align="center", size=12, italic=True, first_line=False, space_after=8)
    t = doc.add_table(rows=len(TEAM), cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, (roll, name) in enumerate(TEAM):
        for j, text in enumerate((roll, name)):
            cell = t.rows[i].cells[j]
            cell.width = Inches(2.35 if j == 0 else 2.55)
            tcPr = cell._tc.get_or_add_tcPr()
            borders = OxmlElement("w:tcBorders")
            for edge in ("top", "left", "bottom", "right"):
                el = OxmlElement(f"w:{edge}")
                el.set(qn("w:val"), "nil")
                borders.append(el)
            tcPr.append(borders)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(text)
            set_run_font(r, size=12)
    add_text(doc, "", align="center", first_line=False, space_after=6)
    add_text(
        doc,
        "in partial fulfillment of the academic requirements for the V Semester course",
        align="center",
        size=12,
        italic=True,
        first_line=False,
        space_after=6,
    )
    add_text(doc, "COMPUTER VISION (23AID301)", align="center", size=12, bold=True, first_line=False, space_after=8)
    add_text(doc, "BACHELOR OF TECHNOLOGY", align="center", size=12, bold=True, italic=True, first_line=False, space_after=1)
    add_text(doc, "IN", align="center", size=12, first_line=False, space_after=1)
    add_text(doc, "COMPUTER SCIENCE AND ENGINEERING", align="center", size=12, first_line=False, space_after=1)
    add_text(
        doc,
        "(ARTIFICIAL INTELLIGENCE AND DATA SCIENCE)",
        align="center",
        size=12,
        first_line=False,
        space_after=10,
    )
    # Logo sits here in the official template (above school block)
    if LOGO.exists():
        add_picture(doc, LOGO, width_in=2.8)
    add_text(doc, "", align="center", first_line=False, space_after=4)
    add_text(doc, "AMRITA SCHOOL OF COMPUTING, BENGALURU", align="center", size=12, bold=True, first_line=False, space_after=1)
    add_text(doc, "AMRITA VISHWA VIDYAPEETHAM", align="center", size=12, bold=True, first_line=False, space_after=1)
    add_text(doc, "BENGALURU 560035", align="center", size=12, first_line=False, space_after=8)
    add_text(doc, "NOVEMBER 2026", align="center", size=12, bold=True, first_line=False, space_after=0)

    doc.add_page_break()

    # ---- Abstract ----
    add_heading_custom(doc, "ABSTRACT", level=0)
    add_text(
        doc,
        "Broadcast football video is single-view and crowded. Referees and operators see contact late, after the players have already closed distance. This project builds a computer-vision pipeline that reads pose and short-horizon motion, scores foul-like challenges against dive-like patterns on short clips, and, when an alert fires, moves a simulated aerial camera toward the threatened pair. The work sits under the course Computer Vision (23AID301).",
    )
    add_text(
        doc,
        "The primary evaluation uses the CAS-FD foul-versus-dive collection after duplicate filtering. The retained split has 351 train, 98 validation, and 95 held-out test clips. Features are causal: only past frames enter the 27-dimensional pair vectors and the 81-dimensional pooled scene vector. Model and cutoff selection use validation only. Two locked clip results are reported. Step 1 is a CatBoost boosted-deep model at a 1.0 s prefix. Step 2 is a soft ensemble at the same cutoff. On the 95-clip test set the final ensemble reaches 64.2% accuracy, 64.6% balanced accuracy, 60.4% precision, 71.1% recall, F1 0.653, average precision 0.650, and ROC AUC 0.671.",
    )
    add_text(
        doc,
        "A secondary continuous track trains on World Cup second halves and tests on Argentina-France. Sample accuracy looks high because of class imbalance, while event F1 stays near 0.061 and ROC AUC near 0.51. That track is reported as an open difficulty, not as the main claim. Supporting checks cover pose coverage on KTH Multiview Football II and planned versus survey camera framing. A desktop demo ships five sample videos, writes replay and telemetry, and shows a live ops dashboard during analysis and replay.",
    )
    add_text(
        doc,
        "Keywords: computer vision; pose estimation; foul anticipation; soft ensemble; virtual camera; CAS-FD; sports broadcast.",
        first_line=False,
        italic=True,
    )

    doc.add_page_break()

    # ---- TOC ----
    add_heading_custom(doc, "TABLE OF CONTENTS", level=0)
    toc = [
        ("ABSTRACT", "i"),
        ("LIST OF FIGURES", "ii"),
        ("LIST OF TABLES", "iii"),
        ("CHAPTER 1 - INTRODUCTION", "1"),
        ("    1.1 Problem background", "1"),
        ("    1.2 Motivation", "2"),
        ("    1.3 Objectives", "2"),
        ("    1.4 Scope and limitations", "3"),
        ("    1.5 Organisation of the report", "3"),
        ("CHAPTER 2 - LITERATURE REVIEW", "4"),
        ("    2.1 Pose estimation in team sports", "4"),
        ("    2.2 Action and foul recognition", "5"),
        ("    2.3 Anticipation and early prediction", "5"),
        ("    2.4 Camera planning for sports", "6"),
        ("    2.5 Summary of gaps", "6"),
        ("CHAPTER 3 - PROPOSED METHODOLOGY", "7"),
        ("    3.1 System overview", "7"),
        ("    3.2 Datasets and splits", "8"),
        ("    3.3 Perception and features", "9"),
        ("    3.4 Clip classification protocol", "10"),
        ("    3.5 Continuous forecasting protocol", "11"),
        ("    3.6 Virtual camera control", "11"),
        ("    3.7 Software requirements", "12"),
        ("    3.8 Hardware requirements", "12"),
        ("CHAPTER 4 - RESULTS AND DISCUSSION", "13"),
        ("    4.1 High-level design", "13"),
        ("    4.2 Low-level design", "14"),
        ("    4.3 Locked CAS-FD results", "15"),
        ("    4.4 Continuous World Cup results", "17"),
        ("    4.5 Supporting pose and camera studies", "18"),
        ("    4.6 Demonstration system", "19"),
        ("CHAPTER 5 - CONCLUSION", "20"),
        ("    5.1 Summary of findings", "20"),
        ("    5.2 Contributions", "20"),
        ("    5.3 Future work", "21"),
        ("REFERENCES", "22"),
        ("APPENDIX A - Locked metric files", "23"),
        ("APPENDIX B - How to run the demo", "24"),
    ]
    for item, page in toc:
        p = doc.add_paragraph()
        set_para(p, align="left", first_line=False, space_after=2, line=1.5)
        run = p.add_run(f"{item}\t{page}")
        set_run_font(run, size=12)

    doc.add_page_break()
    add_heading_custom(doc, "LIST OF FIGURES", level=0)
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
        add_text(doc, f, align="left", first_line=False, space_after=2)

    doc.add_page_break()
    add_heading_custom(doc, "LIST OF TABLES", level=0)
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
    for t in tabs:
        add_text(doc, t, align="left", first_line=False, space_after=2)

    # ===================== CHAPTER 1 =====================
    doc.add_page_break()
    add_heading_custom(doc, "CHAPTER - 1", level=0)
    add_heading_custom(doc, "INTRODUCTION", level=0)

    add_heading_custom(doc, "1.1 Problem background", level=2)
    add_text(
        doc,
        "Football broadcasts are edited for storytelling. The camera rides wide shots, then cuts to close-ups after a challenge has already started. For a computer system that wants to warn before contact, that edit path is hostile. Players occlude each other. Jersey colours collide under stadium lights. The ball and the referee wander through the frame. A model that waits for a clear tackle pose arrives late for any useful camera move.",
    )
    add_text(
        doc,
        "This project treats the problem as two linked tasks. The first is clip-level discrimination of foul-like challenges from dive-like patterns using pose and motion prefixes. The second is continuous scoring on full halves, with an optional virtual skycam that relocates when an alarm fires. The title names the second idea (aerial repositioning driven by precursor prediction). The numbers that hold up for a course claim come mainly from the first task on CAS-FD.",
    )
    add_text(
        doc,
        "CAS-FD supplies short labelled clips. After hashing and perceptual duplicate grouping, 544 clips remain from 600 processed files. The held-out test set has 95 clips (45 foul, 50 dive). SportsD quiet World Cup segments add ordinary-play negatives during training only. Continuous evaluation uses seven FIFA World Cup 2022 second halves aligned to StatsBomb Foul Committed times.",
    )

    add_heading_custom(doc, "1.2 Motivation", level=2)
    add_text(
        doc,
        "Course work in Computer Vision often stops at detection accuracy. Sports production also asks where the camera should look next. If a model can name a threatened pair a second early, a planned viewpoint can reduce body blockage on the replay path. Even when continuous anticipation stays weak, the clip track still gives a measurable foul-versus-dive signal that students can defend with fixed splits and frozen thresholds.",
    )
    add_text(
        doc,
        "We also wanted a runnable demonstration. Markers on a slide do not show timing. The shipped desktop demo plays broadcast beside a pitch simulation, writes telemetry, and updates an ops dashboard while analysis runs. Five sample videos sit in the repository so a fresh clone can open Launch Demo.cmd without downloading the full datasets.",
    )

    add_heading_custom(doc, "1.3 Objectives", level=2)
    add_text(doc, "The project set the following objectives.", first_line=False)
    for obj in [
        "Build a causal pose-and-motion feature pipeline from broadcast or clip video.",
        "Train and select foul-versus-dive classifiers on CAS-FD with validation-only cutoff and threshold choice.",
        "Lock two official clip results (boosted-deep baseline and soft-ensemble final) and report full held-out metrics.",
        "Train a continuous forecaster on World Cup halves and report sample and event metrics honestly.",
        "Implement a simulated aerial camera that relocates on alert and expose the behaviour in a desktop demo with telemetry.",
    ]:
        p = doc.add_paragraph(style="List Number")
        set_para(p, align="justify", first_line=False, space_after=4)
        run = p.add_run(obj)
        set_run_font(run, size=12)

    add_heading_custom(doc, "1.4 Scope and limitations", level=2)
    add_text(
        doc,
        "Scope covers offline analysis of provided clips and halves, frozen joblib models, and a local Tkinter demo. The system does not control a physical drone. Pitch layout without a calibration file is approximate. Continuous positives are rare (47 positive frames among 6,375 on ARG-FRA), so high accuracy without event metrics would mislead. Visual review of the single matched continuous alert shows contact already underway, so clock lead alone is not treated as proof of physiological anticipation.",
    )
    add_text(
        doc,
        "Claims exclude early exploratory clip runs before Step 1, temporary continuous candidates that lost validation selection, and anecdotal demo clips that are not on the official held-out split.",
    )

    add_heading_custom(doc, "1.5 Organisation of the report", level=2)
    add_text(
        doc,
        "Chapter 2 surveys pose estimation, foul recognition, anticipation, and sports camera planning. Chapter 3 describes datasets, features, training protocols, camera control, and software or hardware needs. Chapter 4 presents design diagrams, locked results, plots, and the demo. Chapter 5 concludes and lists future work. References follow IEEE style. Appendices point to locked metric files and demo steps.",
    )

    # ===================== CHAPTER 2 =====================
    doc.add_page_break()
    add_heading_custom(doc, "CHAPTER - 2", level=0)
    add_heading_custom(doc, "LITERATURE REVIEW", level=0)

    add_heading_custom(doc, "2.1 Pose estimation in team sports", level=2)
    add_text(
        doc,
        "Team-sport pose work has moved from pictorial structures and part detectors to deep keypoint models that run at interactive speeds. YOLO-family pose heads give a practical compromise: one forward pass yields boxes and joints for several players. MediaPipe Pose Landmarker supplies denser 3D landmarks once a box is known, which helps display and limb-motion estimates even when the detector cadence stays at a few hertz.",
    )
    add_text(
        doc,
        "Multiview datasets such as KTH Multiview Football II show that a close-up stream recovers limbs that a wide broadcast loses. Sliding tackles remain hard because limbs blur and bodies overlap. Our pose supporting study repeats that pattern: coverage rises when close-up detections merge with wide-field tracks, while tackle sequences still lag.",
    )

    add_heading_custom(doc, "2.2 Action and foul recognition", level=2)
    add_text(
        doc,
        "Foul recognition literature often uses trimmed clips with explicit labels. CAS-FD frames the problem as foul versus dive, which matches a practical dispute in match review. Spatiotemporal CNNs and transformer video models can score whole clips, yet they hide which players drove the decision and they need heavy compute for class projects. Pose graphs and handcrafted kinematic features stay inspectable: separation, closing speed, and limb extension map to language a referee already uses.",
    )
    add_text(
        doc,
        "We keep the clip track on tabular learners (boosted trees, histograms, logistic members) over cached pose features. That choice makes threshold selection and ensemble averaging easy to audit against validation AP.",
    )

    add_heading_custom(doc, "2.3 Anticipation and early prediction", level=2)
    add_text(
        doc,
        "Anticipation means scoring an event before its annotated time using only past evidence. In continuous football halves the positive window is thin. A 0.75-2.00 s lead before StatsBomb Foul Committed yields few positives per minute. Methods that look strong on balanced clip sets often collapse when every second of ordinary play becomes a negative. Alarm logic then matters: refractory intervals and rearms after a below-threshold observation stop a model from chattering.",
    )
    add_text(
        doc,
        "Our continuous protocol selects by event F1 under a ceiling of one false alert per minute on validation halves, then freezes the threshold for ARG-FRA. The resulting event F1 of 0.061 and AUC near 0.51 sit with other hard sports anticipation baselines rather than with the clip numbers.",
    )

    add_heading_custom(doc, "2.4 Camera planning for sports", level=2)
    add_text(
        doc,
        "Automated cameramen optimise framing for ball or player clusters. Less work ties camera choice to foul precursors. A planned skycam can search viewpoints that keep a sightline clear of intervening bodies. Cost terms usually mix blockage, travel distance, and pair separation projected into the view. Smooth motion limits stop the camera from teleporting between optima each frame.",
    )
    add_text(
        doc,
        "In this project the camera module samples candidate positions around the predicted pair, ranks them by blockage and separation, and integrates velocity toward the chosen destination. On reviewed contact brackets the planned view did not beat survey or fixed baselines consistently, largely because early alerts were rare. The planner still gives the demo a concrete relocate behaviour when the clip alarm fires.",
    )

    add_heading_custom(doc, "2.5 Summary of gaps", level=2)
    add_text(
        doc,
        "Published foul classifiers rarely ship a causal prefix protocol with frozen cutoffs and a full confusion table on a stated test split. Continuous anticipation papers sometimes lead with sample accuracy that imbalance inflates. Camera papers seldom connect alerts to a relocate path with logged telemetry. The present work fills those gaps inside one repository: locked metrics, plots, models, and a demo that a classmate can run from demo_samples.",
    )

    # ===================== CHAPTER 3 =====================
    doc.add_page_break()
    add_heading_custom(doc, "CHAPTER - 3", level=0)
    add_heading_custom(doc, "PROPOSED METHODOLOGY", level=0)

    add_heading_custom(doc, "3.1 System overview", level=2)
    add_text(
        doc,
        "Figure 3.1 shows the end-to-end path. Video enters a YOLO11n-pose detector and tracker. PairHistory builds pair and scene features. A clip or continuous scorer emits a scene score. A causal Alarm compares the score with a frozen threshold, then TargetHold keeps the threatened pair for a short horizon. The Camera module plans a destination and renders a virtual skycam panel beside the annotated broadcast. analyze.py writes replay.mp4 and telemetry.jsonl. demo.py mirrors the same numbers on an ops dashboard.",
    )
    add_picture(doc, ASSETS / "fig_pipeline.png", 5.6)
    add_caption(doc, "Figure 3.1 System architecture — end-to-end pipeline")
    add_text(
        doc,
        "Figure 3.1 is the project system diagram from README.md. Input video moves through perception and anticipation, then into the virtual skycam and the demo delivery path (analyze.py, GUI, ops dashboard, and runs/ outputs).",
        first_line=False,
    )

    add_picture(doc, ASSETS / "fig_modules.png", A4_FIG_W)
    add_caption(doc, "Figure 3.2 Module map (Mermaid, from README.md)")
    add_text(
        doc,
        "Figure 3.2 is the repository module map from README.md. core/ feeds training/, frozen models enter evaluation/, and artifacts under models/, research_results/, and demo_samples/ close the loop.",
        first_line=False,
    )

    add_heading_custom(doc, "3.2 Datasets and splits", level=2)
    add_text(
        doc,
        "Table 3.1 lists the retained CAS-FD split after duplicate filtering. Table 3.2 lists continuous match assignments. Positive continuous frames lie 0.75-2.00 s before a StatsBomb Foul Committed timestamp. Pre-match, half-time, and unmatched clock intervals are excluded from continuous scoring windows as described in the experimental notes.",
    )
    add_table(
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
    add_caption(doc, "Table 3.1 CAS-FD retained split counts")

    add_table(
        doc,
        ["Role", "Matches"],
        [
            ["Train", "BRA-SUI, ESP-CRC, FRA-AUS, SRB-SUI"],
            ["Validation", "FRA-DEN, CRC-GER"],
            ["Test", "ARG-FRA final (6,375 samples; 47 positives; 18 fouls)"],
        ],
    )
    add_caption(doc, "Table 3.2 Continuous World Cup match splits")

    add_heading_custom(doc, "3.3 Perception and features", level=2)
    add_text(
        doc,
        "Detection uses YOLO11n-pose. A tracker maintains identities across the analysis cadence (2 Hz for clip feature caching). Shot-cut resets clear tracks when histogram signatures jump. Close-player detections merge with wide tracks for display. For each nearby pair (up to eight), the system builds a 27-D vector from separation, approach or closing speed, relative motion, limb angles and extension, joint confidence, and short-horizon temporal change. An 81-D scene vector pools those pairs. No future frames, event labels, filenames, or scoreboard clocks enter as numeric inputs.",
    )
    add_text(
        doc,
        "MediaPipe supplies hip-relative 3D landmarks inside player boxes when confidence allows. Leg-motion magnitudes feed the camera focus heuristic during alerts. Missing 3D pose falls back to a vertical stick figure in the skycam view.",
    )

    add_heading_custom(doc, "3.4 Clip classification protocol", level=2)
    add_text(
        doc,
        "Clips are decoded and pose or pair states are cached at 2 Hz. A prefix sample is taken at cutoff times 1.0, 1.5, or 2.0 s. Training uses train-split prefixes with multi-time augmentation. Validation alone selects the model family, cutoff, and decision threshold. The threshold raises the worst of accuracy, balanced accuracy, F1, precision, and recall on validation. Final selection among boosted and soft-ensemble families stays inside a near-best validation AP band. The 95-clip test set is evaluated once.",
    )
    add_text(
        doc,
        "Step 1 locks CatBoost boosted-deep at 1.0 s. Step 2 locks soft-ensemble (probability average of CatBoost, tree, and logistic members) at 1.0 s with threshold approximately 0.328. Integrity rules forbid test-set hyperparameter fitting.",
    )

    add_heading_custom(doc, "3.5 Continuous forecasting protocol", level=2)
    add_text(
        doc,
        "Candidates fit on four training halves. Validation halves choose model and threshold by event F1 under at most one false alert per minute, breaking ties by average precision. The selected model is L2-regularised logistic regression with C = 0.0005 and threshold 0.018414. ARG-FRA is tested once. Alarms rearm after a below-threshold observation and keep a two-second refractory interval. Time gaps and shot changes reset state.",
    )

    add_heading_custom(doc, "3.6 Virtual camera control", level=2)
    add_text(
        doc,
        "When a pair is held under alert, the camera samples destinations on a ring around the mean future position of the pair at two heights. Each candidate pays for blockage along the sightline, travel distance from the current xyz, and gains credit for separating the two targets in the projected view. Velocity integrates toward the lowest-cost destination under acceleration limits. Without an alert the camera surveys a wide orbit behind the median player cluster. Trails and destinations are logged for the dashboard map.",
    )

    add_heading_custom(doc, "3.7 Software requirements", level=2)
    add_table(
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
    add_caption(doc, "Table 3.3 Software stack used in the project")

    add_heading_custom(doc, "3.8 Hardware requirements", level=2)
    add_text(
        doc,
        "Training and plotting ran on a standard Windows workstation with a CUDA-capable GPU preferred for pose extraction and CPU fallback available through Scout('CPU'). The demo runs on CPU once models are frozen. Disk space is dominated by datasets when present; the public repository ships models, prepared caches, research_results, and demo_samples instead of raw training video.",
    )

    # ===================== CHAPTER 4 =====================
    doc.add_page_break()
    add_heading_custom(doc, "CHAPTER - 4", level=0)
    add_heading_custom(doc, "RESULTS AND DISCUSSION", level=0)

    add_heading_custom(doc, "4.1 High-level design", level=2)
    add_text(
        doc,
        "At a high level the system is a feed of video into perception, a branch into clip or continuous scoring, and a delivery path that couples alerts to camera motion and UI telemetry. Figure 3.1 already stated that layout. Figure 4.1 packages the locked evaluations into one overview image used during project review.",
    )
    add_picture(doc, PLOTS / "overview_dashboard.png", A4_FIG_W)
    add_caption(doc, "Figure 4.1 Overview dashboard of locked evaluations")
    add_text(
        doc,
        "Figure 4.1 summarises clip and continuous headline metrics side by side. Readers should treat the continuous panel as a hard baseline while reading the clip panel as the primary result.",
        first_line=False,
    )

    add_heading_custom(doc, "4.2 Low-level design", level=2)
    add_text(
        doc,
        "Low-level modules map as follows. vision.py and video_pose.py detect and track. anticipation.py and in_play.py own PairHistory, BroadcastFeatures, Alarm, and TargetHold. video_controller.py loads frozen models and returns a score plus ranked pair. camera.py owns destination search and rendering. analyze.py orchestrates a clip, writes panels at 1280x418, and streams compact telemetry to the UI. dashboard.py draws risk, warning, and skycam map widgets. fit_video.py and match_training.py produce the joblib artifacts consumed at runtime.",
    )
    add_text(
        doc,
        "Figure 4.2 shows retained clip counts by split and class. The slight foul/dive imbalance in training (151 vs 200) is visible; the test set is nearly balanced (45 vs 50).",
    )
    add_picture(doc, PLOTS / "clip_split_counts.png", 5.4)
    add_caption(doc, "Figure 4.2 CAS-FD train / validation / test clip counts")

    add_heading_custom(doc, "4.3 Locked CAS-FD results", level=2)
    add_table(
        doc,
        ["Step", "Model", "Prefix", "Role"],
        [
            ["1", "boosted-deep (CatBoost)", "1.0 s", "Pre-finetune baseline"],
            ["2", "soft-ensemble", "1.0 s", "Locked final classifier"],
        ],
    )
    add_caption(doc, "Table 4.1 Locked clip models and cutoffs")

    add_text(
        doc,
        "Table 4.2 compares held-out test metrics. Step 2 improves accuracy, balanced accuracy, precision, recall, F1, and average precision. ROC AUC moves from 0.676 to 0.671, a small drop while the operating point gains recall and F1. Figure 4.3 plots the same comparison.",
    )
    add_table(
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
    add_caption(doc, "Table 4.2 Held-out CAS-FD test comparison (95 clips)")

    add_picture(doc, PLOTS / "locked_clip_comparison.png", 5.6)
    add_caption(doc, "Figure 4.3 Locked Step-1 versus Step-2 comparison")
    add_text(
        doc,
        "Figure 4.3 makes the Step-2 lift visible on classification metrics. Primary final values sit in the roughly 60-71% band on the full official test split, which matches the honest target set for this course project.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_test_metrics.png", 5.4)
    add_caption(doc, "Figure 4.4 Final soft-ensemble test metrics")
    add_text(
        doc,
        "Figure 4.4 focuses on the final ensemble alone. The operating threshold is approximately 0.32825 at cutoff 1.0 s.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_pr.png", 5.0)
    add_caption(doc, "Figure 4.5 Precision-recall curve (clip test)")
    add_text(
        doc,
        "Figure 4.5 shows the precision-recall trade-off on the 95-clip test set. Average precision is 0.650 for the locked final model.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_roc.png", 5.0)
    add_caption(doc, "Figure 4.6 ROC curve (clip test)")
    add_text(
        doc,
        "Figure 4.6 reports ROC AUC 0.671. Ranking quality stays moderate; the chosen threshold prefers recall for the foul-positive class.",
        first_line=False,
    )

    add_table(
        doc,
        ["", "Predicted dive / neg", "Predicted foul / pos"],
        [
            ["True dive / neg", "29", "21"],
            ["True foul / pos", "13", "32"],
        ],
    )
    add_caption(doc, "Table 4.3 Final confusion counts (soft-ensemble)")

    add_picture(doc, PLOTS / "clip_confusion.png", 4.4)
    add_caption(doc, "Figure 4.7 Confusion matrix (clip test)")
    add_text(
        doc,
        "Table 4.3 and Figure 4.7 agree: 32 true fouls are caught, 13 are missed, 21 dives are false alarms, and 29 dives are correct negatives. False alarms remain the main practical cost for a review tool.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_scores.png", 5.2)
    add_caption(doc, "Figure 4.8 Score distributions (clip test)")
    add_text(
        doc,
        "Figure 4.8 shows score overlap between classes. Separation exists but is incomplete, which explains why accuracy stays near the mid-60% range rather than climbing into the high 80s.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_prefix_sensitivity.png", 5.4)
    add_caption(doc, "Figure 4.9 Prefix sensitivity study")
    add_text(
        doc,
        "Figure 4.9 compares cutoffs. Validation selected 1.0 s for both locked steps. Longer prefixes give the model more motion history and also move closer to contact, which changes the meaning of anticipation.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "clip_bootstrap_ci.png", 5.2)
    add_caption(doc, "Figure 4.10 Bootstrap confidence intervals")
    add_text(
        doc,
        "Figure 4.10 reports bootstrap intervals around test metrics. Intervals are wide on a 95-clip set, so small gaps between Step 1 and Step 2 should be read cautiously even when the point estimates favour the ensemble.",
        first_line=False,
    )

    add_heading_custom(doc, "4.4 Continuous World Cup results", level=2)
    add_text(
        doc,
        "Tables 4.4 and 4.5 record the ARG-FRA test. Sample accuracy of 98.6% is imbalance theatre: balanced accuracy is 0.507 and AP is 0.0106. Event matching finds 1 hit, 14 false alerts, and 17 misses among 18 fouls. Event F1 is 0.061. False alerts per minute are 0.264 under the frozen threshold.",
    )
    add_table(
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
    add_caption(doc, "Table 4.4 Continuous sample-level metrics (ARG-FRA)")

    add_table(
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
    add_caption(doc, "Table 4.5 Continuous event-level metrics (18 fouls)")

    add_picture(doc, PLOTS / "continuous_sample_metrics.png", 5.2)
    add_caption(doc, "Figure 4.11 Continuous sample-level metrics")
    add_picture(doc, PLOTS / "continuous_event_metrics.png", 5.2)
    add_caption(doc, "Figure 4.12 Continuous event-level metrics")
    add_text(
        doc,
        "Figures 4.11 and 4.12 visualise the same numbers. They are included so the continuous track cannot be mistaken for a success claim during viva discussion.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "continuous_score_timeline.png", A4_FIG_W)
    add_caption(doc, "Figure 4.13 Continuous score timeline (ARG-FRA)")
    add_text(
        doc,
        "Figure 4.13 plots score against match time with foul markers. Peaks rarely align with the annotated events under the chosen threshold, which matches the low event recall.",
        first_line=False,
    )

    add_heading_custom(doc, "4.5 Supporting pose and camera studies", level=2)
    add_picture(doc, PLOTS / "pose_pck_coverage.png", 5.4)
    add_caption(doc, "Figure 4.14 Pose PCK / coverage on KTH")
    add_text(
        doc,
        "Figure 4.14 shows that merging close-up detections with wide-field tracks raises coverage on run sequences. Sliding-tackle frames stay difficult. That finding guided the dual-pass detection path used in analyze.py.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "camera_evaluation.png", 5.4)
    add_caption(doc, "Figure 4.15 Virtual camera evaluation")
    add_text(
        doc,
        "Figure 4.15 compares planned, survey, and fixed cameras on reviewed events. The planned view does not win consistently. Early alerts were scarce, so the planner often never received a clean precursor window. The module remains part of the demo because relocate behaviour is still visible when the clip alarm fires.",
        first_line=False,
    )

    add_picture(doc, PLOTS / "anticipation_curves.png", 5.8)
    add_caption(doc, "Figure 4.16 Anticipation curve pack")
    add_text(
        doc,
        "Figure 4.16 packs anticipation-related curves used in the paper-style export. Together with Figures 4.5 and 4.6 it supports ranking discussion without relying on a single scalar.",
        first_line=False,
    )

    add_heading_custom(doc, "4.6 Demonstration system", level=2)
    add_text(
        doc,
        "The desktop demo lists five shipped clips (Table 4.6). Run analysis loads pose and forecasting models, streams progress, and updates the ops dashboard at a capped rate so the UI stays responsive. After completion, Replay syncs each frame of replay.mp4 with telemetry.jsonl. The dashboard shows foul risk against threshold, soft elevated risk versus hard onset warning, and skycam states SURVEY, RELOCATING, and LOCKED ON with a mini pitch map.",
    )
    add_table(
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
    add_caption(doc, "Table 4.6 Demo sample clips shipped with the repository")
    add_text(
        doc,
        "Outputs land under runs/<timestamp>/: replay.mp4, telemetry.jsonl, summary.json, and optional incident.mp4 when FFmpeg is installed. Launch Demo.cmd sets PYTHONPATH to the project virtualenv site-packages and starts demo.py.",
        first_line=False,
    )

    # ===================== CHAPTER 5 =====================
    doc.add_page_break()
    add_heading_custom(doc, "CHAPTER - 5", level=0)
    add_heading_custom(doc, "CONCLUSION", level=0)

    add_heading_custom(doc, "5.1 Summary of findings", level=2)
    add_text(
        doc,
        "On the full held-out CAS-FD test set the locked soft-ensemble classifier reaches about 64% accuracy, 65% F1, 71% recall, 60% precision, 65% AP, and 67% ROC AUC at a 1.0 s prefix. The Step-1 boosted-deep model already cleared the 60% band; Step 2 improves most classification metrics further. Continuous foul anticipation on ARG-FRA stays near chance on event metrics and should be presented as an open challenge. Pose coverage benefits from close-up fusion. Planned camera gains were inconsistent on reviewed events.",
    )

    add_heading_custom(doc, "5.2 Contributions", level=2)
    for c in [
        "A causal pose-feature pipeline with validation-only model and threshold selection for foul-versus-dive clips.",
        "Two locked result sets (boosted-deep and soft-ensemble) with full tables, curves, and confusion counts.",
        "An honest continuous World Cup evaluation with sample and event metrics side by side.",
        "A virtual skycam planner wired to alerts, plus a desktop demo with live ops dashboard and five runnable samples.",
    ]:
        p = doc.add_paragraph(style="List Number")
        set_para(p, align="justify", first_line=False, space_after=4)
        run = p.add_run(c)
        set_run_font(run, size=12)

    add_heading_custom(doc, "5.3 Future work", level=2)
    add_text(
        doc,
        "Stronger continuous models will need better positive mining, calibrated multi-view input, and perhaps learned camera policies trained with visibility rewards. Clip performance may rise with temporal transformers over pose tracks if compute allows, provided the same validation-only discipline remains. A calibrated pitch homography for every demo clip would tighten the skycam geometry. Physical UAV control lies outside this course deliverable.",
    )

    # ===================== REFERENCES =====================
    doc.add_page_break()
    add_heading_custom(doc, "REFERENCES", level=0)
    refs = [
        'G. Jocher et al., "Ultralytics YOLO," GitHub repository, 2024. [Online]. Available: https://github.com/ultralytics/ultralytics',
        'C. Lugaresi et al., "MediaPipe: A framework for building perception pipelines," arXiv:1906.08172, 2019.',
        'L. Prokhorenkova, G. Gusev, A. Vorobev, A. V. Dorogush, and A. Gulin, "CatBoost: unbiased boosting with categorical features," in Proc. NeurIPS, 2018.',
        'F. Pedregosa et al., "Scikit-learn: Machine learning in Python," JMLR, vol. 12, pp. 2825-2830, 2011.',
        'StatsBomb, "StatsBomb Open Data," GitHub repository. [Online]. Available: https://github.com/statsbomb/open-data',
        'J. H. et al., "CAS-FD foul-versus-dive dataset," Hugging Face Datasets. [Online]. Available: https://huggingface.co/datasets/jahid114593/foul-vs-dive-dataset',
        'A. Wu et al., "SportsD," Hugging Face Datasets. [Online]. Available: https://huggingface.co/datasets/addisonwu05/sportsd',
        'V. Kazemi, M. Burenius, H. Azizpour, and J. Sullivan, "Multi-view body part recognition with random forests," in Proc. BMVC, 2013. (KTH Multiview Football context)',
        'Wikipedia contributors, "Signs of AI writing," Wikipedia. [Online]. Available: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing',
        "Amrita Vishwa Vidyapeetham, School of Computing, Bengaluru, Course 23AID301 Computer Vision, V Semester project guidelines, 2026.",
        "Project repository: Forensic Sky-Robotics. [Online]. Available: https://github.com/dedsecpy/Forensic-Sky-Robotics",
        "OpenCV team, OpenCV Library documentation. [Online]. Available: https://docs.opencv.org/",
    ]
    for i, r in enumerate(refs, 1):
        p = doc.add_paragraph()
        set_para(p, align="justify", first_line=False, space_after=6)
        run = p.add_run(f"[{i}] {r}")
        set_run_font(run, size=11)

    # ===================== APPENDIX =====================
    doc.add_page_break()
    add_heading_custom(doc, "APPENDIX A", level=0)
    add_heading_custom(doc, "Locked metric files", level=1)
    add_text(
        doc,
        "Numeric locks live under research_results/. locked_clip_results.json stores Step-1 and Step-2 headline numbers. video_metrics.json and continuous_metrics.json hold fuller dumps. PNG figures used in Chapter 4 sit in research_results/plots/. Models are models/video_anticipation.joblib and models/match_anticipation.joblib. The markdown companion report.md mirrors the locked narrative for repository readers.",
    )

    doc.add_page_break()
    add_heading_custom(doc, "APPENDIX B", level=0)
    add_heading_custom(doc, "How to run the demo", level=1)
    add_text(
        doc,
        "Clone the repository. Install requirements into a Python 3.11 environment. On Windows, double-click Launch Demo.cmd, or set PYTHONPATH to .venv\\Lib\\site-packages and run python demo.py. Choose a shipped clip from the dropdown, click Run analysis, watch the ops dashboard, then use Replay or Open results. Offline analysis: python analyze.py demo_samples\\world_cup_final.mp4. Full dataset download is required only to reproduce training, not to run the demonstration.",
    )
    add_text(
        doc,
        "Title-page authors: Aejaz Ahmad Ansari (BL.AI.U4AID24078), Mutyala Jahnavi Sai (BL.AI.U4AID24047), Divyesh Shanmugarajah (BL.AI.U4AID24083). Architecture figures 3.1-3.3 are Mermaid diagrams rendered to PNG and sized for A4.",
        first_line=False,
        italic=True,
    )

    # Footer on body pages only (different first page keeps the cover clean like the template)
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    # blank first-page footer
    ff = section.first_page_footer
    if ff.paragraphs:
        ff.paragraphs[0].text = ""
    footer = section.footer
    fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.text = ""
    run = fp.add_run("Dept. of CSE, ASC, Bengaluru  |  23AID301 Computer Vision  |  Forensic Sky-Robotics")
    set_run_font(run, size=9)

    try:
        doc.save(str(OUT))
        print("Wrote", OUT)
    except PermissionError:
        doc.save(str(OUT_ALT))
        print("Wrote", OUT_ALT, "(original file was locked/open)")


if __name__ == "__main__":
    build()
