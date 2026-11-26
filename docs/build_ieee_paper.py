"""Build IEEE double-column paper from Team 19 Project Report CV.docx only.

No new prose: body text, captions, tables, and references are taken from the source.
IEEE labels (Abstract—, Index Terms—, I./A. heading style) are formatting only.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, Twips

SRC = Path(r"C:\Users\Work\Desktop\Team 19 Project Report CV.docx")
ASSETS = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\ieee_assets")
OUT = Path(r"C:\Users\Work\Desktop\Team 19 IEEE Paper_v4.docx")
OUT_ALT = Path(
    r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\Team_19_IEEE_Paper.docx"
)
OUT_DESKTOP = Path(r"C:\Users\Work\Desktop\Team 19 IEEE Paper.docx")

# IEEE US-letter conference margins (inches)
MARGIN_TOP = 0.75
MARGIN_BOTTOM = 1.0
MARGIN_SIDE = 0.625
COL_GAP_TWIPS = 360  # 0.25 in
FIG_W = 3.3  # single-column figure width


def set_run_font(run, size=10, bold=False, italic=False, name="Times New Roman"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def add_para(
    doc,
    text="",
    *,
    size=10,
    bold=False,
    italic=False,
    align="justify",
    space_after=6,
    space_before=0,
    first_indent=False,
):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = 1.0
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.first_line_indent = Inches(0.14) if first_indent and text else Inches(0)
    # Prevent Word from leaving empty column gaps by dragging blocks to the next page
    pf.keep_together = False
    pf.keep_with_next = False
    pf.page_break_before = False
    pf.widow_control = False
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    if text:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, italic=italic)
    return p


def add_mixed_para(doc, parts, *, align="justify", space_after=6, first_indent=False):
    """parts: list of (text, bold, italic, size)."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    pf.line_spacing = 1.0
    pf.first_line_indent = Inches(0.14) if first_indent else Inches(0)
    pf.keep_together = False
    pf.keep_with_next = False
    pf.page_break_before = False
    pf.widow_control = False
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
    }[align]
    for text, bold, italic, size in parts:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, italic=italic)
    return p


def heading1(doc, roman: str, title: str):
    # IEEE: centered, small caps look via ALL CAPS, 10 pt bold
    add_para(
        doc,
        f"{roman}. {title.upper()}",
        size=10,
        bold=True,
        align="center",
        space_before=12,
        space_after=6,
    )


def heading2(doc, letter: str, title: str):
    # IEEE: italic, left, 10 pt
    add_para(
        doc,
        f"{letter}. {title}",
        size=10,
        bold=True,
        italic=True,
        align="left",
        space_before=8,
        space_after=4,
    )


def caption_fig(doc, text: str):
    add_para(doc, text, size=8, italic=True, align="center", space_after=8, space_before=2)


def caption_tbl(doc, text: str):
    add_para(doc, text.upper() if text.lower().startswith("table") else text, size=8, bold=True, align="center", space_before=8, space_after=4)


def add_picture(doc, path: Path, width=FIG_W):
    if not path.exists():
        add_para(doc, f"[Missing: {path.name}]", size=8, italic=True, align="center")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.keep_with_next = False
    p.paragraph_format.keep_together = False
    p.paragraph_format.page_break_before = False
    p.add_run().add_picture(str(path), width=Inches(width))


def clear_cell_borders(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag == qn("w:tcBorders"):
            tcPr.remove(child)


def copy_table(doc, src_table, font_size=8):
    rows = [[c.text.strip() for c in row.cells] for row in src_table.rows]
    if not rows:
        return
    cols = len(rows[0])
    t = doc.add_table(rows=len(rows), cols=cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            set_run_font(r, size=font_size, bold=(i == 0))
    add_para(doc, "", space_after=4)


def set_section_margins(section):
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(MARGIN_TOP)
    section.bottom_margin = Inches(MARGIN_BOTTOM)
    section.left_margin = Inches(MARGIN_SIDE)
    section.right_margin = Inches(MARGIN_SIDE)


def set_columns(section, num: int, space_twips: int = COL_GAP_TWIPS):
    sectPr = section._sectPr
    # remove existing cols
    for child in list(sectPr):
        if child.tag == qn("w:cols"):
            sectPr.remove(child)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num))
    if num > 1:
        cols.set(qn("w:space"), str(space_twips))
        cols.set(qn("w:equalWidth"), "1")
    sectPr.append(cols)


def _twips(inches: float) -> str:
    """OOXML page/margin attributes use twips (1/20 pt), not EMUs."""
    return str(int(inches * 1440))


def add_continuous_section_break(doc):
    """Insert continuous section break; new section becomes active for following content."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    # Keep the break paragraph invisible/zero-height as much as Word allows
    r = p.add_run()
    set_run_font(r, size=1)
    pPr = p._p.get_or_add_pPr()
    sectPr = OxmlElement("w:sectPr")
    # one-column geometry for the section that ENDS here (title block)
    pgSz = OxmlElement("w:pgSz")
    pgSz.set(qn("w:w"), _twips(8.5))
    pgSz.set(qn("w:h"), _twips(11))
    sectPr.append(pgSz)
    pgMar = OxmlElement("w:pgMar")
    pgMar.set(qn("w:top"), _twips(MARGIN_TOP))
    pgMar.set(qn("w:right"), _twips(MARGIN_SIDE))
    pgMar.set(qn("w:bottom"), _twips(MARGIN_BOTTOM))
    pgMar.set(qn("w:left"), _twips(MARGIN_SIDE))
    pgMar.set(qn("w:header"), "720")
    pgMar.set(qn("w:footer"), "720")
    pgMar.set(qn("w:gutter"), "0")
    sectPr.append(pgMar)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), "1")
    cols.set(qn("w:space"), "720")
    sectPr.append(cols)
    type_el = OxmlElement("w:type")
    type_el.set(qn("w:val"), "continuous")
    sectPr.append(type_el)
    pPr.append(sectPr)
    return p


def T(paras, i: int) -> str:
    return (paras[i] or "").strip()


def _no_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag == qn("w:tcBorders"):
            tcPr.remove(child)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tcPr.append(borders)


def _cell_line(cell, text, *, size=8, bold=False, italic=False, underline=False, space_after=0):
    p = cell.add_paragraph() if cell.paragraphs[0].text else cell.paragraphs[0]
    if cell.paragraphs[0].text and p is cell.paragraphs[0] and cell.paragraphs[0].runs:
        p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    set_run_font(r, size=size, bold=bold, italic=italic)
    r.font.underline = underline
    return p


FULL_W = Inches(8.5 - 2 * MARGIN_SIDE)  # spans both columns in a 2-col section


def _set_table_full_width(table, width=FULL_W):
    """Force table wider than one column so Word spans it across both columns."""
    table.autofit = False
    table.allow_autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    if tbl.tblPr is None:
        tbl.insert(0, tblPr)
    for child in list(tblPr):
        if child.tag == qn("w:tblW"):
            tblPr.remove(child)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(int(width.twips)))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)


def add_author_block(doc, members):
    """IEEE-style stacked author columns in a single-column header section."""
    n = len(members)
    t = doc.add_table(rows=1, cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_full_width(t)
    col_w = FULL_W / n
    for j, m in enumerate(members):
        cell = t.rows[0].cells[j]
        _no_borders(cell)
        cell.width = col_w
        cell.text = ""
        p0 = cell.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_after = Pt(1)
        p0.paragraph_format.keep_with_next = False
        r = p0.add_run(m["name"])
        set_run_font(r, size=10, bold=False)

        for line in m["affiliation"]:
            p = cell.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = False
            rr = p.add_run(line)
            set_run_font(rr, size=8, italic=True)

        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = False
        er = p.add_run(m["email"])
        set_run_font(er, size=8, italic=False)
        er.font.underline = True


def build():
    src = Document(str(SRC))
    paras = [p.text for p in src.paragraphs]
    tables = src.tables

    doc = Document()
    set_section_margins(doc.sections[0])
    set_columns(doc.sections[0], 1)

    # ---- Title + authors in ONE column (full page width) ----
    add_para(doc, T(paras, 1), size=18, bold=True, align="center", space_after=8, space_before=0)

    affiliation = [
        "Department of Computer Science and Engineering",
        "Amrita School of Computing",
        "Amrita Vishwa Vidyapeetham",
        "Bengaluru, India",
    ]
    members = []
    for row in tables[0].rows:
        roll = row.cells[0].text.strip()
        name = row.cells[1].text.strip()
        email = f"{roll.lower()}@bl.students.amrita.edu"
        members.append({"name": name, "affiliation": affiliation, "email": email})
    add_author_block(doc, members)

    # Continuous break → two-column body on the SAME page
    add_continuous_section_break(doc)
    body_sec = doc.sections[-1]
    set_section_margins(body_sec)
    set_columns(body_sec, 2, COL_GAP_TWIPS)

    # ---- Abstract (source 19–21) + Index Terms (source 22) ----
    abstract_body = " ".join(t for t in (T(paras, 19), T(paras, 20), T(paras, 21)) if t)
    add_mixed_para(
        doc,
        [("Abstract—", True, True, 9), (abstract_body, False, False, 9)],
        align="justify",
        space_after=4,
    )
    keywords = T(paras, 22)
    # Source line begins with leftover word "Electronic"; keep source text as-is after label.
    add_mixed_para(
        doc,
        [("Index Terms—", True, True, 9), (keywords, False, True, 9)],
        align="justify",
        space_after=6,
    )

    # ===================== I. INTRODUCTION =====================
    heading1(doc, "I", "Introduction")
    heading2(doc, "A", "Problem background")
    for i in (60, 61, 62):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "B", "Motivation")
    for i in (64, 65):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "C", "Objectives")
    add_para(doc, T(paras, 67), size=10, first_indent=True)
    for i in (68, 69, 70, 71, 72):
        add_para(doc, "• " + T(paras, i), size=10, align="left", space_after=3)
    heading2(doc, "D", "Scope and limitations")
    for i in (74, 75):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "E", "Organisation of the report")
    add_para(doc, T(paras, 77), size=10, first_indent=True)

    # ===================== II. LITERATURE REVIEW =====================
    heading1(doc, "II", "Literature Review")
    heading2(doc, "A", "Team Sports Pose Estimation")
    for i in (82, 83):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "B", "Recognition of action and foul")
    for i in (85, 86):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "C", "Anticipation and early prediction")
    for i in (88, 89):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "D", "Planning sports shots with the camera")
    for i in (91, 92):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    heading2(doc, "E", "Summary of gaps")
    add_para(doc, T(paras, 94), size=10, first_indent=True)

    # ===================== III. PROPOSED METHODOLOGY =====================
    heading1(doc, "III", "Proposed Methodology")
    heading2(doc, "A", "System overview")
    add_para(doc, T(paras, 99), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_02.png", FIG_W)
    caption_fig(doc, T(paras, 101))
    add_para(doc, T(paras, 102), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_03.jpg", FIG_W)
    caption_fig(doc, T(paras, 104))
    add_para(doc, T(paras, 105), size=10, first_indent=True)

    heading2(doc, "B", "Datasets and splits")
    add_para(doc, T(paras, 107), size=10, first_indent=True)
    caption_tbl(doc, T(paras, 109))
    copy_table(doc, tables[2])
    caption_tbl(doc, T(paras, 111))
    copy_table(doc, tables[3])

    heading2(doc, "C", "Perception and features")
    for i in (114, 115):
        add_para(doc, T(paras, i), size=10, first_indent=True)

    heading2(doc, "D", "Clip classification protocol")
    for i in (117, 118):
        add_para(doc, T(paras, i), size=10, first_indent=True)

    heading2(doc, "E", "Continuous forecasting protocol")
    add_para(doc, T(paras, 120), size=10, first_indent=True)

    heading2(doc, "F", "Virtual camera control")
    add_para(doc, T(paras, 122), size=10, first_indent=True)

    heading2(doc, "G", "Software requirements")
    caption_tbl(doc, T(paras, 125))
    copy_table(doc, tables[4])

    heading2(doc, "H", "Hardware requirements")
    add_para(doc, T(paras, 127), size=10, first_indent=True)

    # ===================== IV. RESULTS AND DISCUSSION =====================
    heading1(doc, "IV", "Results and Discussion")
    heading2(doc, "A", "High-level design")
    add_para(doc, T(paras, 132), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_04.png", FIG_W)
    caption_fig(doc, T(paras, 134))
    add_para(doc, T(paras, 135), size=10, first_indent=True)

    heading2(doc, "B", "Low-level design")
    for i in (137, 138):
        add_para(doc, T(paras, i), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_05.png", FIG_W)
    caption_fig(doc, T(paras, 140))

    heading2(doc, "C", "Locked CAS-FD results")
    caption_tbl(doc, T(paras, 143))
    copy_table(doc, tables[5])
    add_para(doc, T(paras, 144), size=10, first_indent=True)
    caption_tbl(doc, T(paras, 146))
    copy_table(doc, tables[6])
    add_picture(doc, ASSETS / "img_06.png", FIG_W)
    caption_fig(doc, T(paras, 148))
    add_para(doc, T(paras, 149), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_07.png", FIG_W)
    caption_fig(doc, T(paras, 151))
    add_para(doc, T(paras, 152), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_08.png", FIG_W)
    caption_fig(doc, T(paras, 154))
    add_para(doc, T(paras, 155), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_09.png", FIG_W)
    caption_fig(doc, T(paras, 157))
    add_para(doc, T(paras, 158), size=10, first_indent=True)
    caption_tbl(doc, T(paras, 160))
    copy_table(doc, tables[7])
    add_picture(doc, ASSETS / "img_10.png", FIG_W)
    caption_fig(doc, T(paras, 162))
    add_para(doc, T(paras, 163), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_11.png", FIG_W)
    caption_fig(doc, T(paras, 165))
    add_para(doc, T(paras, 166), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_12.png", FIG_W)
    caption_fig(doc, T(paras, 168))
    add_para(doc, T(paras, 169), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_13.png", FIG_W)
    caption_fig(doc, T(paras, 171))
    add_para(doc, T(paras, 172), size=10, first_indent=True)

    heading2(doc, "D", "Continuous World Cup results")
    add_para(doc, T(paras, 174), size=10, first_indent=True)
    caption_tbl(doc, T(paras, 177))
    copy_table(doc, tables[8])
    caption_tbl(doc, T(paras, 179))
    copy_table(doc, tables[9])
    add_picture(doc, ASSETS / "img_14.png", FIG_W)
    caption_fig(doc, T(paras, 181))
    add_picture(doc, ASSETS / "img_15.png", FIG_W)
    caption_fig(doc, T(paras, 183))
    add_para(doc, T(paras, 184), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_16.png", FIG_W)
    caption_fig(doc, T(paras, 186))
    add_para(doc, T(paras, 187), size=10, first_indent=True)

    heading2(doc, "E", "Supporting pose and camera studies")
    add_picture(doc, ASSETS / "img_17.png", FIG_W)
    caption_fig(doc, T(paras, 190))
    add_para(doc, T(paras, 191), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_18.png", FIG_W)
    caption_fig(doc, T(paras, 193))
    add_para(doc, T(paras, 194), size=10, first_indent=True)
    add_picture(doc, ASSETS / "img_19.png", FIG_W)
    caption_fig(doc, T(paras, 196))
    add_para(doc, T(paras, 197), size=10, first_indent=True)

    heading2(doc, "F", "Demonstration system")
    add_para(doc, T(paras, 199), size=10, first_indent=True)
    caption_tbl(doc, T(paras, 201))
    copy_table(doc, tables[10])
    add_para(doc, T(paras, 202), size=10, first_indent=True)

    # ===================== V. CONCLUSION =====================
    heading1(doc, "V", "Conclusion")
    heading2(doc, "A", "Summary of findings")
    add_para(doc, T(paras, 207), size=10, first_indent=True)
    heading2(doc, "B", "Contributions")
    for i in (209, 210, 211, 212):
        add_para(doc, "• " + T(paras, i), size=10, align="left", space_after=3)
    heading2(doc, "C", "Future work")
    add_para(doc, T(paras, 214), size=10, first_indent=True)

    # ===================== REFERENCES =====================
    heading1(doc, "VI", "References")
    # Keep reference lines exactly as in source (216 is heading; 217–228 are entries)
    for i in range(217, 229):
        t = T(paras, i)
        if t:
            add_para(doc, t, size=8, align="left", space_after=3)

    # ===================== APPENDIX (source) =====================
    heading1(doc, "VII", "Appendix")
    add_para(doc, T(paras, 233), size=10, bold=True, italic=True, align="left", space_after=4)
    add_para(doc, T(paras, 234), size=10, first_indent=True)
    add_para(doc, T(paras, 235), size=10, first_indent=True)
    add_para(doc, T(paras, 237), size=10, first_indent=True)
    add_para(doc, T(paras, 238), size=9, align="left", space_after=6)

    doc.save(str(OUT))
    doc.save(str(OUT_ALT))
    print("wrote", OUT)
    print("wrote", OUT_ALT)
    try:
        doc.save(str(OUT_DESKTOP))
        print("wrote", OUT_DESKTOP)
    except PermissionError:
        print("desktop original locked; use", OUT)


if __name__ == "__main__":
    build()
