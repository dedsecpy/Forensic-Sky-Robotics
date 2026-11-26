"""Fill the Chilli IEEE Word template with Team 19 report content only."""
from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

TEMPLATE = Path(
    r"E:\For Publish\Chilli Project (K Sirisha)\An AI-Based Interactive Chilli Disease Identification Assistant Using MobileNetV3 and Bayesian Agentic Reasoning.docx"
)
SRC = Path(r"C:\Users\Work\Desktop\Team 19 Project Report CV.docx")
ASSETS = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\ieee_assets")
OUT = Path(r"C:\Users\Work\Desktop\Team 19 IEEE Paper.docx")
OUT_ALT = Path(r"E:\AIDS\Sem 5\23AID301_Computer_Vision\End Sem Project\docs\Team_19_IEEE_Paper.docx")

FIG_W = 3.15


def T(paras, i: int) -> str:
    return (paras[i] or "").strip()


def clear_body_keep_final_sectpr(doc: Document):
    body = doc.element.body
    final = None
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            final = child
        body.remove(child)
    if final is not None:
        body.append(final)


def extract_template_sectprs(tpl: Document):
    """Return sectPr copies in template order: title_1col, authors_3col, body_2col, final_2col."""
    found = []
    for child in tpl.element.body:
        # paragraph-embedded sectPr
        if child.tag == qn("w:p"):
            for s in child.iter(qn("w:sectPr")):
                found.append(deepcopy(s))
        elif child.tag == qn("w:sectPr"):
            found.append(deepcopy(child))
    # Probe order: [title/1col-ish, authors/3, body/2, final/2]
    title_1 = found[0] if len(found) > 0 else None
    authors_3 = next((s for s in found if (s.find(qn("w:cols")) is not None and s.find(qn("w:cols")).get(qn("w:num")) == "3")), None)
    twos = [s for s in found if (s.find(qn("w:cols")) is not None and s.find(qn("w:cols")).get(qn("w:num")) == "2")]
    body_2 = twos[0] if twos else None
    final_2 = twos[-1] if twos else None
    return title_1, authors_3, body_2, final_2


def add_break_para(doc: Document, sectpr):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    pPr = p._p.get_or_add_pPr()
    pPr.append(deepcopy(sectpr))
    return p


def set_run_font(run, size=None, bold=None, italic=None, name="Times New Roman"):
    run.font.name = name
    if run._element.rPr is not None:
        run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def para(doc, text, style="Normal", *, align=None, space_after=None, first_indent=False):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.keep_together = False
    pf.keep_with_next = False
    pf.page_break_before = False
    pf.widow_control = False
    if space_after is not None:
        pf.space_after = Pt(space_after)
    if first_indent:
        pf.first_line_indent = Inches(0.14)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    elif align == "left":
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if text:
        # clear default
        if p.runs:
            p.clear()
        r = p.add_run(text)
        # let style control size mostly; ensure TNR
        set_run_font(r, name="Times New Roman")
    return p


def author_block(doc, name, lines, style="Author"):
    text = "\n".join([name] + lines)
    p = doc.add_paragraph(style=style)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.clear()
    # name
    r = p.add_run(name + "\n")
    set_run_font(r, size=9, bold=False)
    for i, line in enumerate(lines):
        end = "" if i == len(lines) - 1 else "\n"
        rr = p.add_run(line + end)
        set_run_font(rr, size=8, italic=(i < len(lines) - 1))
        if i == len(lines) - 1:
            rr.font.underline = True
            set_run_font(rr, size=8, italic=False)
    return p


def no_borders(cell):
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


def add_picture(doc, path: Path, width=FIG_W):
    if not path.exists():
        para(doc, f"[Missing figure: {path.name}]", align="center")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = False
    p.paragraph_format.keep_together = False
    p.add_run().add_picture(str(path), width=Inches(width))


def copy_table(doc, src_table):
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
            set_run_font(r, size=8, bold=(i == 0))
    doc.add_paragraph()


def build():
    tpl = Document(str(TEMPLATE))
    title_1_sect, authors_3_sect, body_2_sect, final_2_sect = extract_template_sectprs(tpl)

    src = Document(str(SRC))
    paras = [p.text for p in src.paragraphs]
    tables = src.tables

    # Write to a fresh output path first to avoid partial/locked desktop file
    out_write = OUT
    try:
        shutil.copy2(TEMPLATE, out_write)
    except PermissionError:
        out_write = OUT.with_name("Team 19 IEEE Paper_from_template.docx")
        shutil.copy2(TEMPLATE, out_write)

    doc = Document(str(out_write))
    clear_body_keep_final_sectpr(doc)
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            body.remove(child)
    if final_2_sect is not None:
        body.append(deepcopy(final_2_sect))

    # ---- Title (single-column section) ----
    p = para(doc, T(paras, 1), style="Author", align="center", space_after=6)
    if p.runs:
        set_run_font(p.runs[0], size=22, bold=True)
    para(doc, "", style="Author", space_after=0)
    if title_1_sect is not None:
        add_break_para(doc, title_1_sect)

    # Affiliation lines derived only from report title-page fields
    affiliation = [
        "Department of Computer Science and Engineering",
        "Amrita School of Computing,",
        "Amrita Vishwa Vidyapeetham, Bengaluru, India",
    ]
    members = []
    for row in tables[0].rows:
        roll = row.cells[0].text.strip()
        name = row.cells[1].text.strip()
        email = f"{roll.lower()}@bl.students.amrita.edu"
        members.append((name, affiliation + [email]))

    for name, lines in members:
        author_block(doc, name, lines, style="Author")

    # End 3-column author section, then 2-column body
    add_break_para(doc, authors_3_sect)
    add_break_para(doc, body_2_sect)

    # ---- Abstract / Keywords from report only ----
    abstract_body = " ".join(t for t in (T(paras, 19), T(paras, 20), T(paras, 21)) if t)
    para(doc, "Abstract—" + abstract_body, style="Abstract", space_after=4)
    # Index terms: report para 22 as-is after Keywords— label used by template style
    kw = T(paras, 22)
    # Template uses Keywords—; report line is the keyword list (may start with Electronic...)
    if kw.lower().startswith("keywords"):
        para(doc, kw, style="Abstract", space_after=6)
    else:
        para(doc, "Keywords—" + kw, style="Abstract", space_after=6)

    # ---- Body: report chapters only; headings via template styles ----
    # I. Introduction
    para(doc, "Introduction", style="Heading 1")
    para(doc, "A. Problem background", style="Heading 2")
    for i in (60, 61, 62):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "B. Motivation", style="Heading 2")
    for i in (64, 65):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "C. Objectives", style="Heading 2")
    para(doc, T(paras, 67), first_indent=True, space_after=3)
    for i in (68, 69, 70, 71, 72):
        para(doc, T(paras, i), style="List Paragraph", space_after=2)
    para(doc, "D. Scope and limitations", style="Heading 2")
    for i in (74, 75):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "E. Organisation of the report", style="Heading 2")
    para(doc, T(paras, 77), first_indent=True, space_after=4)

    # II. Literature Review
    para(doc, "Literature Review", style="Heading 1")
    para(doc, "A. Team Sports Pose Estimation", style="Heading 2")
    for i in (82, 83):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "B. Recognition of action and foul", style="Heading 2")
    for i in (85, 86):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "C. Anticipation and early prediction", style="Heading 2")
    for i in (88, 89):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "D. Planning sports shots with the camera", style="Heading 2")
    for i in (91, 92):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    para(doc, "E. Summary of gaps", style="Heading 2")
    para(doc, T(paras, 94), first_indent=True, space_after=4)

    # III. Proposed Methodology
    para(doc, "Proposed Methodology", style="Heading 1")
    para(doc, "A. System overview", style="Heading 2")
    para(doc, T(paras, 99), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_02.png")
    para(doc, T(paras, 101), align="center", space_after=4)  # figure caption text from report
    para(doc, T(paras, 102), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_03.jpg")
    para(doc, T(paras, 104), align="center", space_after=4)
    para(doc, T(paras, 105), first_indent=True, space_after=4)

    para(doc, "B. Datasets and splits", style="Heading 2")
    para(doc, T(paras, 107), first_indent=True, space_after=4)
    para(doc, T(paras, 109), align="center", space_after=2)
    copy_table(doc, tables[2])
    para(doc, T(paras, 111), align="center", space_after=2)
    copy_table(doc, tables[3])

    para(doc, "C. Perception and features", style="Heading 2")
    for i in (114, 115):
        para(doc, T(paras, i), first_indent=True, space_after=4)

    para(doc, "D. Clip classification protocol", style="Heading 2")
    for i in (117, 118):
        para(doc, T(paras, i), first_indent=True, space_after=4)

    para(doc, "E. Continuous forecasting protocol", style="Heading 2")
    para(doc, T(paras, 120), first_indent=True, space_after=4)

    para(doc, "F. Virtual camera control", style="Heading 2")
    para(doc, T(paras, 122), first_indent=True, space_after=4)

    para(doc, "G. Software requirements", style="Heading 2")
    para(doc, T(paras, 125), align="center", space_after=2)
    copy_table(doc, tables[4])

    para(doc, "H. Hardware requirements", style="Heading 2")
    para(doc, T(paras, 127), first_indent=True, space_after=4)

    # IV. Results and Discussion
    para(doc, "Results and Discussion", style="Heading 1")
    para(doc, "A. High-level design", style="Heading 2")
    para(doc, T(paras, 132), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_04.png")
    para(doc, T(paras, 134), align="center", space_after=4)
    para(doc, T(paras, 135), first_indent=True, space_after=4)

    para(doc, "B. Low-level design", style="Heading 2")
    for i in (137, 138):
        para(doc, T(paras, i), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_05.png")
    para(doc, T(paras, 140), align="center", space_after=4)

    para(doc, "C. Locked CAS-FD results", style="Heading 2")
    para(doc, T(paras, 143), align="center", space_after=2)
    copy_table(doc, tables[5])
    para(doc, T(paras, 144), first_indent=True, space_after=4)
    para(doc, T(paras, 146), align="center", space_after=2)
    copy_table(doc, tables[6])
    add_picture(doc, ASSETS / "img_06.png")
    para(doc, T(paras, 148), align="center", space_after=4)
    para(doc, T(paras, 149), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_07.png")
    para(doc, T(paras, 151), align="center", space_after=4)
    para(doc, T(paras, 152), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_08.png")
    para(doc, T(paras, 154), align="center", space_after=4)
    para(doc, T(paras, 155), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_09.png")
    para(doc, T(paras, 157), align="center", space_after=4)
    para(doc, T(paras, 158), first_indent=True, space_after=4)
    para(doc, T(paras, 160), align="center", space_after=2)
    copy_table(doc, tables[7])
    add_picture(doc, ASSETS / "img_10.png")
    para(doc, T(paras, 162), align="center", space_after=4)
    para(doc, T(paras, 163), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_11.png")
    para(doc, T(paras, 165), align="center", space_after=4)
    para(doc, T(paras, 166), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_12.png")
    para(doc, T(paras, 168), align="center", space_after=4)
    para(doc, T(paras, 169), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_13.png")
    para(doc, T(paras, 171), align="center", space_after=4)
    para(doc, T(paras, 172), first_indent=True, space_after=4)

    para(doc, "D. Continuous World Cup results", style="Heading 2")
    para(doc, T(paras, 174), first_indent=True, space_after=4)
    para(doc, T(paras, 177), align="center", space_after=2)
    copy_table(doc, tables[8])
    para(doc, T(paras, 179), align="center", space_after=2)
    copy_table(doc, tables[9])
    add_picture(doc, ASSETS / "img_14.png")
    para(doc, T(paras, 181), align="center", space_after=4)
    add_picture(doc, ASSETS / "img_15.png")
    para(doc, T(paras, 183), align="center", space_after=4)
    para(doc, T(paras, 184), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_16.png")
    para(doc, T(paras, 186), align="center", space_after=4)
    para(doc, T(paras, 187), first_indent=True, space_after=4)

    para(doc, "E. Supporting pose and camera studies", style="Heading 2")
    add_picture(doc, ASSETS / "img_17.png")
    para(doc, T(paras, 190), align="center", space_after=4)
    para(doc, T(paras, 191), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_18.png")
    para(doc, T(paras, 193), align="center", space_after=4)
    para(doc, T(paras, 194), first_indent=True, space_after=4)
    add_picture(doc, ASSETS / "img_19.png")
    para(doc, T(paras, 196), align="center", space_after=4)
    para(doc, T(paras, 197), first_indent=True, space_after=4)

    para(doc, "F. Demonstration system", style="Heading 2")
    para(doc, T(paras, 199), first_indent=True, space_after=4)
    para(doc, T(paras, 201), align="center", space_after=2)
    copy_table(doc, tables[10])
    para(doc, T(paras, 202), first_indent=True, space_after=4)

    # V. Conclusion
    para(doc, "Conclusion", style="Heading 1")
    para(doc, "A. Summary of findings", style="Heading 2")
    para(doc, T(paras, 207), first_indent=True, space_after=4)
    para(doc, "B. Contributions", style="Heading 2")
    for i in (209, 210, 211, 212):
        para(doc, T(paras, i), style="List Paragraph", space_after=2)
    para(doc, "C. Future work", style="Heading 2")
    para(doc, T(paras, 214), first_indent=True, space_after=4)

    # References (report lines only)
    para(doc, "References", style="Heading 1")
    for i in range(217, 229):
        t = T(paras, i)
        if t:
            para(doc, t, style="references", space_after=2)

    # Appendix text from report only
    para(doc, "Appendix", style="Heading 1")
    para(doc, T(paras, 233), style="Heading 2")
    para(doc, T(paras, 234), first_indent=True, space_after=4)
    para(doc, T(paras, 235), first_indent=True, space_after=4)
    para(doc, T(paras, 237), first_indent=True, space_after=2)
    para(doc, T(paras, 238), space_after=4)

    # Save
    doc.save(str(out_write))
    doc.save(str(OUT_ALT))
    if out_write != OUT:
        try:
            shutil.copy2(out_write, OUT)
        except PermissionError:
            print("desktop primary locked; use", out_write)
    print("wrote", out_write)
    print("wrote", OUT_ALT)


if __name__ == "__main__":
    build()
