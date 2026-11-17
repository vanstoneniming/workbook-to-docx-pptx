"""Build the Word deliverable: 试题册（每节末集中答案）+ 知识网络.  """
import os, json, sys, re
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_BREAK
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image
import layout

OUT = None
BODY_FONT = "宋体"
HEAD_FONT = "黑体"
LATIN = "Times New Roman"
GRAY = RGBColor(0x80, 0x80, 0x80)


def set_run_font(run, name=BODY_FONT, size=10.5, bold=False, color=None, latin=LATIN):
    run.font.name = latin
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    r = run._element.rPr.rFonts
    r.set(qn("w:eastAsia"), name)


def para(doc, text="", size=10.5, bold=False, align=None, indent=0.0, first_line=0.0,
         space_before=0, space_after=2, font=BODY_FONT, color=None, line=1.35):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if indent:
        pf.left_indent = Cm(indent)
    if first_line:
        pf.first_line_indent = Cm(first_line)
    if text:
        set_run_font(p.add_run(text), font, size, bold, color)
    return p


def add_field(paragraph, instr):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    t = OxmlElement("w:t")
    t.text = "1"
    r = OxmlElement("w:r")
    r.append(t)
    fld.append(r)
    paragraph._p.append(fld)


def setup_page(doc, book_title):
    sec = doc.sections[0]
    sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(2.2); sec.bottom_margin = Cm(2.0)
    # header
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run_font(hp.add_run(book_title), HEAD_FONT, 9, False, RGBColor(0x59, 0x59, 0x59))
    pPr = hp._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "AAAAAA")
    bdr.append(bottom); pPr.append(bdr)
    # footer
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(fp.add_run("第 "), BODY_FONT, 9, color=GRAY)
    add_field(fp, "PAGE")
    set_run_font(fp.add_run(" 页　共 "), BODY_FONT, 9, color=GRAY)
    add_field(fp, "NUMPAGES")
    set_run_font(fp.add_run(" 页"), BODY_FONT, 9, color=GRAY)


def cover(doc, title, subtitle, lines):
    for _ in range(4):
        para(doc, "", space_after=0)
    p = para(doc, title, size=26, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
             font=HEAD_FONT, space_after=10)
    p2 = para(doc, subtitle, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, font=HEAD_FONT,
              color=RGBColor(0x1F, 0x4E, 0x79), space_after=24)
    for ln in lines:
        para(doc, ln, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, space_after=4)


def chapter_head(doc, title):
    doc.add_page_break()
    p = para(doc, title, size=21, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
             font=HEAD_FONT, space_before=6, space_after=14)
    # decorative rule
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:space"), "6"); bottom.set(qn("w:color"), "1F4E79")
    bdr.append(bottom); pPr.append(bdr)


def section_head(doc, title, page_from, page_to):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(2)
    set_run_font(p.add_run(title), HEAD_FONT, 15, True)
    rng = f"原书 P{page_from:03d}" if page_from == page_to else f"原书 P{page_from:03d}–P{page_to:03d}"
    para(doc, rng, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, space_after=8)


def group_head(doc, label):
    p = para(doc, label, size=11, bold=True, font=HEAD_FONT, space_before=8, space_after=4)
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "2"); bottom.set(qn("w:color"), "BFBFBF")
    bdr.append(bottom); pPr.append(bdr)


def add_image(doc, path, max_w_cm=12.0, max_h_cm=7.2, caption=None):
    if not path or not os.path.exists(path):
        return
    im = Image.open(path)
    w, h = im.size
    wcm = max_w_cm
    hcm = wcm * h / w
    if hcm > max_h_cm:
        hcm = max_h_cm; wcm = hcm * w / h
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(path, width=Cm(wcm))
    if caption:
        para(doc, caption, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, space_after=4)


def question(doc, q, show_page=True):
    body_lines, items = layout.split_stem(q.get("stem") or [])
    first = body_lines[0] if body_lines else ""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.first_line_indent = Cm(0.74)
    if show_page and q.get("page"):
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.4), WD_TAB_ALIGNMENT.RIGHT)
    set_run_font(p.add_run(f"{q['no']}. "), BODY_FONT, 10.5, True)
    if q.get("lead"):
        set_run_font(p.add_run(layout.nbsp_bracket(q["lead"]) + " "), "楷体", 10.5, latin="KaiTi")
    if first:
        set_run_font(p.add_run(layout.nbsp_bracket(first)), BODY_FONT, 10.5)
    if show_page and q.get("page"):
        set_run_font(p.add_run("\t"), BODY_FONT, 8)
        set_run_font(p.add_run(f"P{q['page']:03d}"), BODY_FONT, 8.5, color=GRAY)

    for extra in body_lines[1:]:
        para(doc, layout.nbsp_bracket(extra), size=10.5, indent=0.74, space_after=1, line=1.35)

    if items:
        write_rows(doc, items, 10.5)
    for sub in q.get("subs") or []:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.35
        p.paragraph_format.left_indent = Cm(1.48)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(1)
        set_run_font(p.add_run(f"（{sub['no']}）"), BODY_FONT, 10.5, True)
        set_run_font(p.add_run(layout.nbsp_bracket("".join(sub["text"]))), BODY_FONT, 10.5)

    figs = [f for f in q.get("figs", []) if f.get("file") and os.path.exists(f["file"])]
    if figs:
        per_row = 1 if len(figs) == 1 else (2 if len(figs) <= 4 else 3)
        max_h = 7.2 if len(figs) == 1 else (4.6 if len(figs) <= 2 else (3.6 if len(figs) <= 4 else 3.0))
        row_w = 12.6
        for i in range(0, len(figs), per_row):
            row = figs[i:i + per_row]
            cell_w = row_w / per_row - 0.25
            tbl = doc.add_table(rows=1, cols=len(row))
            tbl.autofit = False
            for j, f in enumerate(row):
                cell = tbl.cell(0, j)
                cell.width = Cm(row_w / per_row)
                cp = cell.paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.paragraph_format.space_before = Pt(2)
                cp.paragraph_format.space_after = Pt(2)
                im = Image.open(f["file"])
                w0, h0 = im.size
                wcm = cell_w; hcm = wcm * h0 / w0
                if hcm > max_h:
                    hcm = max_h; wcm = hcm * w0 / h0
                cp.add_run().add_picture(f["file"], width=Cm(wcm))

    opts = [f"{c}. {layout.nbsp_bracket(t)}" for c, t in (q.get("options") or [])]
    if opts:
        write_rows(doc, opts, 10.5)


def write_rows(doc, texts, size, total_cm=12.6):
    cols = layout.choose_cols(texts, total_cm / 2.54, size * 0.9)
    colw = total_cm / cols
    for r in range(0, len(texts), cols):
        row = texts[r:r + cols]
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.left_indent = Cm(1.48)
        p.paragraph_format.space_after = Pt(1)
        for i in range(1, cols):
            p.paragraph_format.tab_stops.add_tab_stop(Cm(1.48 + colw * i / 2.54))
        for i, t in enumerate(row):
            if i:
                p.add_run("\t")
            set_run_font(p.add_run(t), BODY_FONT, size)


def answer_block(doc, ans, groups):
    if not ans or (not ans.get("choice") and not ans.get("comp")):
        return
    p = para(doc, "【参考答案】", size=10.5, bold=True, font=HEAD_FONT, space_before=12, space_after=4)
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single"); top.set(qn("w:sz"), "8")
    top.set(qn("w:space"), "4"); top.set(qn("w:color"), "1F4E79")
    bdr.append(top); pPr.append(bdr)
    if ans.get("choice"):
        items = sorted(ans["choice"].items(), key=lambda kv: int(kv[0]))
        chunks = []
        for i in range(0, len(items), 5):
            part = items[i:i + 5]
            chunks.append(f"{part[0][0]}—{part[-1][0]}　" + "　".join(v for _, v in part))
        para(doc, "选择题：" + "　　".join(chunks), size=10, space_after=3,
             first_line=0.0, indent=0.0)
    if ans.get("comp"):
        for no in sorted(ans["comp"], key=lambda x: int(x)):
            lines = [l for l in ans["comp"][no] if l.strip()]
            if not lines:
                continue
            para(doc, f"{no}. " + lines[0], size=10, indent=0.0, space_after=1, line=1.3)
            for ln in lines[1:]:
                para(doc, ln, size=10, indent=0.5, space_after=1, line=1.3)


def build(book, out_path, title, subtitle, lines):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = LATIN
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    setup_page(doc, title)
    cover(doc, title, subtitle, lines)
    for c in book:
        chapter_head(doc, c["title"])
        for s in c["sections"]:
            qs = [q for g in s["groups"] for q in g["questions"]]
            pages = [q["page"] for q in qs if q.get("page")]
            pf, pt_ = (min(pages), max(pages)) if pages else (s.get("page", 1), s.get("page", 1))
            section_head(doc, s["title"], pf, pt_)
            for nf in s.get("net_files", []):
                add_image(doc, nf, max_w_cm=15.0, max_h_cm=9.0)
                break
            for g in s["groups"]:
                group_head(doc, g["label"])
                for q in g["questions"]:
                    question(doc, q)
            answer_block(doc, s.get("ans"), s["groups"])
    doc.save(out_path)
    return out_path


def run(model_path, out_path, title, subtitle, note):
    book = json.load(open(model_path, encoding="utf-8"))
    return build(book, out_path, title, subtitle, [note, "据原书整理　页码对应原书印刷页码"])
