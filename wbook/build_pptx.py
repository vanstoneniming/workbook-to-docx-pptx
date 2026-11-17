"""Build the 16:9 projection deck: one question per slide, answer on the next slide."""
import os, json, math, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn, nsdecls
from pptx.oxml import parse_xml
from PIL import Image
from . import layout

OUT = None
IMG_PPT = None

INK = RGBColor(0x1B, 0x25, 0x33)
NAVY = RGBColor(0x12, 0x2A, 0x47)
ACCENT = RGBColor(0xC8, 0x4B, 0x31)
ACCENT2 = RGBColor(0x2E, 0x86, 0x8B)
LIGHT = RGBColor(0xF6, 0xF4, 0xEF)
GRAY = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "微软雅黑"

TOP = 0.98            # content top
BOTTOM = 7.16         # content bottom
LEFT = 1.55
WIDTH_FULL = 11.35
WIDTH_COL = 7.25      # when figures sit on the right


def prep_images():
    os.makedirs(IMG_PPT, exist_ok=True)
    for root, _, files in os.walk(os.path.join(OUT, "fig")):
        for f in files:
            if not f.lower().endswith(".png"):
                continue
            src = os.path.join(root, f)
            dst = os.path.join(IMG_PPT, re.sub(r"[^0-9A-Za-z_.]", "_",
                                               os.path.relpath(src, os.path.join(OUT, "fig")))[:-4] + ".jpg")
            if not os.path.exists(dst):
                im = Image.open(src).convert("RGB")
                w, h = im.size
                if w > 1400:
                    im = im.resize((1400, int(h * 1400 / w)), Image.LANCZOS)
                im.save(dst, quality=86)


def jpg_path(png):
    if not png:
        return None
    rel = os.path.relpath(png, os.path.join(OUT, "fig"))
    return os.path.join(IMG_PPT, re.sub(r"[^0-9A-Za-z_.]", "_", rel)[:-4] + ".jpg")


def set_ea(run, name):
    rPr = run._r.get_or_add_rPr()
    for tag in ("ea", "cs"):
        el = rPr.find(qn("a:" + tag))
        if el is None:
            el = parse_xml('<a:%s %s typeface="%s"/>' % (tag, nsdecls("a"), name))
            rPr.append(el)
        else:
            el.set("typeface", name)


def textbox(slide, x, y, w, h, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT,
            anchor=MSO_ANCHOR.TOP, spacing=1.25, ea=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    for i, ln in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = FONT
        r.font.color.rgb = color
        if ea:
            set_ea(r, ea)
    return tb


def rect(slide, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def badge(slide, x, y, d, text, color, size=22):
    b = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    b.fill.solid(); b.fill.fore_color.rgb = color
    b.line.fill.background(); b.shadow.inherit = False
    tf = b.text_frame
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = str(text)
    r.font.size = Pt(size if len(str(text)) < 3 else size - 4)
    r.font.bold = True; r.font.name = FONT; r.font.color.rgb = WHITE


def cover(prs, title, subtitle, note):
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, NAVY)
    rect(s, 0.9, 2.05, 0.09, 2.2, ACCENT)
    textbox(s, 1.25, 1.95, 10.6, 1.0, title, 34, WHITE, True)
    textbox(s, 1.28, 3.05, 10.6, 0.7, subtitle, 20, RGBColor(0xE8, 0xC8, 0x8A))
    textbox(s, 1.28, 4.2, 10.6, 0.9, note, 13, RGBColor(0xA8, 0xB4, 0xC4))


def brand_slide(prs, brand):
    """封底：公众号名片。"""
    if not brand:
        return
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, NAVY)
    rect(s, 0.9, 2.15, 0.09, 1.9, ACCENT)
    textbox(s, 1.25, 2.05, 8.4, 0.9, brand.get("name", ""), 36, WHITE, True)
    if brand.get("line1"):
        textbox(s, 1.28, 3.0, 8.4, 0.5, brand["line1"], 15, RGBColor(0xE8, 0xC8, 0x8A))
    if brand.get("line2"):
        textbox(s, 1.28, 3.55, 8.4, 0.45, brand["line2"], 14, RGBColor(0xA8, 0xB4, 0xC4))
    if brand.get("short"):
        textbox(s, 1.28, 4.35, 7.9, 1.6, brand["short"], 13, RGBColor(0xC9, 0xD2, 0xDE), spacing=1.5)
    links = brand.get("links") or []
    if links:
        rect(s, 0, 6.5, 13.333, 1.0, LIGHT)
        tb = s.shapes.add_textbox(Inches(1.1), Inches(6.82), Inches(11.2), Inches(0.4))
        tf = tb.text_frame
        tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        for i, ln in enumerate(links):
            if i:
                r0 = p.add_run(); r0.text = "　·　"
                r0.font.size = Pt(12); r0.font.name = FONT
                r0.font.color.rgb = RGBColor(0x9A, 0xA3, 0xAE)
                set_ea(r0, FONT)
            r = p.add_run(); r.text = ln["text"]
            r.font.size = Pt(13); r.font.name = FONT
            r.font.color.rgb = ACCENT2
            set_ea(r, FONT)
            r.hyperlink.address = ln["url"]
    qr = brand.get("qrcode")
    if qr and os.path.exists(qr):
        s.shapes.add_picture(qr, Inches(9.9), Inches(3.05), height=Inches(2.2))
        textbox(s, 9.9, 5.35, 2.2, 0.4, "扫码关注", 12, RGBColor(0xA8, 0xB4, 0xC4), align=PP_ALIGN.CENTER)


def chapter(prs, idx, title, count):
    s = blank(prs)
    rect(s, 0, 0, 13.333, 7.5, NAVY)
    textbox(s, 1.0, 2.4, 2.0, 1.2, f"{idx:02d}", 60, RGBColor(0x2E, 0x4A, 0x6B), True)
    textbox(s, 2.35, 2.6, 9.6, 1.2, title, 30, WHITE, True)
    rect(s, 2.4, 3.75, 2.2, 0.05, ACCENT)
    textbox(s, 2.4, 4.0, 9.0, 0.5, f"共 {count} 题", 14, RGBColor(0xA8, 0xB4, 0xC4))


def q_text(q):
    parts = []
    if q.get("lead"):
        parts.append(q["lead"])
    body, items = layout.split_stem(q.get("stem") or [])
    parts.extend(body)
    return layout.nbsp_bracket("\n".join(parts))


def pick_font(q, width_in, avail_h, sizes=(30, 28, 26, 24, 22, 20, 19, 18, 17, 16, 15, 14, 13)):
    for fs in sizes:
        blocks = layout.layout_question(q, width_in, fs, max(12, fs - 3), max(11, fs - 4))
        if layout.measure(blocks) <= avail_h:
            return fs
    return sizes[-1]


def draw_blocks(slide, blocks, width_in, fs, start=TOP, x=LEFT):
    y = start
    for kind, payload, h in blocks:
        if kind == "lead":
            textbox(slide, x, y, width_in, h + 0.05, payload, fs, RGBColor(0x33, 0x3A, 0x45),
                    spacing=1.32, ea="楷体")
            y += h + 0.1
        elif kind == "body":
            size = fs
            textbox(slide, x, y, width_in, h + 0.05, payload, size, INK, spacing=1.3)
            y += h + 0.1
        elif kind == "sub":
            size = max(11, fs - 4)
            textbox(slide, x, y, width_in, h + 0.05, payload, size, INK, spacing=1.3)
            y += h + 0.08
        else:                      # option / item row
            row, cols = payload
            size = max(12, fs - 3)
            colw = width_in / cols
            for i, item in enumerate(row):
                textbox(slide, x + i * colw, y, colw - 0.1, h + 0.05, item, size, INK, spacing=1.28)
            y += h + 0.08
    return y


def paginate(blocks, capacity):
    pages, cur, used = [], [], 0.0
    for b in blocks:
        if cur and used + b[2] > capacity:
            pages.append(cur); cur, used = [], 0.0
        cur.append(b); used += b[2]
    if cur:
        pages.append(cur)
    return pages


def question_slides(prs, q, head, sec_name):
    figs = [f for f in q.get("figs", []) if f.get("file") and os.path.exists(jpg_path(f.get("file")))]
    single_wide = any(f.get("panel") for f in figs)
    if len(figs) == 1:
        im = Image.open(jpg_path(figs[0]["file"]))
        single_wide = single_wide or im.size[1] / im.size[0] < 1.02
    width = WIDTH_FULL if (not figs or single_wide) else WIDTH_COL
    capacity = (BOTTOM - TOP) * 0.97 if (not figs or single_wide) else (BOTTOM - TOP) * 0.97

    if single_wide:
        # 图在下：文字先占一部分高度，其余给图
        fs = pick_font(q, width, capacity * 0.5)
        blocks = layout.layout_question(q, width, fs, max(12, fs - 3), max(11, fs - 4))
        avail_text = 7.5 - TOP - 0.35
        pages = paginate(blocks, avail_text)
        for i, page in enumerate(pages):
            s = blank(prs)
            paint_frame(s, sec_name, head, q["no"], cont=i > 0)
            used = draw_blocks(s, page, width, fs)
            if i == len(pages) - 1:
                place_bottom_figures(s, figs, used)
        return

    fs = pick_font(q, width, capacity)
    blocks = layout.layout_question(q, width, fs, max(12, fs - 3), max(11, fs - 4))
    pages = paginate(blocks, capacity)
    for i, page in enumerate(pages):
        s = blank(prs)
        paint_frame(s, sec_name, head, q["no"], cont=i > 0)
        draw_blocks(s, page, width, fs)
        if figs and i == 0:
            place_right_figures(s, figs)
        elif figs and i == len(pages) - 1 and len(figs) < 3:
            pass


def place_right_figures(s, figs):
    right_x = LEFT + WIDTH_COL + 0.32
    right_w = 13.333 - right_x - 0.55
    n = len(figs)
    slot = (BOTTOM - TOP) / n
    cy = TOP
    for f in figs:
        pth = jpg_path(f["file"])
        im = Image.open(pth)
        w_in = right_w; h_in = w_in * im.size[1] / im.size[0]
        if h_in > slot - 0.16:
            h_in = slot - 0.16; w_in = h_in * im.size[0] / im.size[1]
        s.shapes.add_picture(pth, Inches(right_x + (right_w - w_in) / 2),
                             Inches(cy + (slot - h_in) / 2), width=Inches(w_in))
        cy += slot


def place_bottom_figures(s, figs, y_text_end):
    if not figs:
        return
    y = max(y_text_end + 0.14, TOP + 1.1)
    avail_h = BOTTOM - y
    if avail_h < 0.9:
        return
    n = len(figs[:2])
    slot_w = WIDTH_FULL / n
    for i, f in enumerate(figs[:2]):
        pth = jpg_path(f["file"])
        im = Image.open(pth)
        w_in = slot_w - 0.2
        h_in = w_in * im.size[1] / im.size[0]
        if h_in > avail_h:
            h_in = avail_h; w_in = h_in * im.size[0] / im.size[1]
        if h_in < 0.7:
            continue
        x = LEFT + i * slot_w + (slot_w - w_in) / 2
        s.shapes.add_picture(pth, Inches(x), Inches(y + (avail_h - h_in) / 2), width=Inches(w_in))


def paint_frame(s, sec_name, head, no, cont=False, answer=False):
    rect(s, 0, 0, 13.333, 7.5, LIGHT)
    rect(s, 0, 0, 0.22, 7.5, ACCENT if answer else ACCENT2)
    textbox(s, 0.75, 0.42, 8.6, 0.34, sec_name, 12, GRAY)
    tag = f"{head}　·　第 {no} 题" + ("　答案" if answer else "") + ("　续" if cont else "")
    textbox(s, 8.6, 0.42, 4.1, 0.34, tag, 12, GRAY, align=PP_ALIGN.RIGHT)
    badge(s, 0.58, 0.95, 0.74, "答" if answer else no, ACCENT2 if answer else ACCENT,
          18 if answer else 22)


def answer_text(q, ans):
    if not ans or not ans.get("text"):
        return "（参考答案见 Word 版）"
    return ans["text"]


def answer_slides(prs, q, ans, head, sec_name):
    text = answer_text(q, ans)
    qs = q_text(q)
    qfont = 24
    while True:
        qh = layout.est_lines(qs, 11.2, qfont) * qfont * 1.35 * 1.12 / 72
        if qh <= 4.3 or qfont <= 13:
            break
        qfont -= 1
    if qh > 4.2:
        keep, acc = [], 0.0
        for ln in qs.split("\n"):
            acc += layout.est_lines(ln, 11.2, qfont) * qfont * 1.35 * 1.12 / 72
            if acc > 4.0:
                break
            keep.append(ln)
        qs = "\n".join(keep + ["……"])
        qh = layout.est_lines(qs, 11.2, qfont) * qfont * 1.35 * 1.12 / 72
    y_div = min(max(TOP + qh + 0.3, 2.6), 5.5)
    avail = max(1.3, BOTTOM - y_div - 0.45)
    fs = 34
    for cand in (34, 30, 28, 26, 24, 22, 20, 18, 16, 15, 14):
        h = layout.est_lines(text, 10.9, cand) * cand * 1.35 * 1.12 / 72
        if h <= avail:
            fs = cand
            break
    else:
        fs = 14
    s = blank(prs)
    paint_frame(s, sec_name, head, q["no"], answer=True)
    textbox(s, LEFT, TOP, 11.2, qh + 0.1, qs, qfont, RGBColor(0x4A, 0x52, 0x5E), spacing=1.35)
    rect(s, LEFT, y_div, 11.2, 0.02, RGBColor(0xD8, 0xD2, 0xC6))
    rect(s, LEFT, y_div + 0.2, 0.09, avail - 0.1, ACCENT2)
    textbox(s, LEFT + 0.25, y_div + 0.3, 10.9, avail, text, fs,
            RGBColor(0x8C, 0x2F, 0x1E), True, spacing=1.35)


def net_slides(prs, files, sec_name, ch_title):
    """一页（或两页）知识网络，整块裁图铺满可用区。"""
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return
    groups = [files] if len(files) == 1 else [[f] for f in files]
    for gi, grp in enumerate(groups):
        s = blank(prs)
        rect(s, 0, 0, 13.333, 7.5, LIGHT)
        rect(s, 0, 0, 0.22, 7.5, ACCENT2)
        textbox(s, 0.75, 0.42, 8.6, 0.34, sec_name, 12, GRAY)
        textbox(s, 8.6, 0.42, 4.1, 0.34, ch_title, 12, GRAY, align=PP_ALIGN.RIGHT)
        textbox(s, 0.95, 0.92, 4.0, 0.5, "知识网络", 24, INK, True)
        rect(s, 0.98, 1.48, 1.5, 0.05, ACCENT)
        y = 1.75
        avail_h = BOTTOM - y
        avail_w = 11.4
        im = Image.open(grp[0])
        w_in = avail_w; h_in = w_in * im.size[1] / im.size[0]
        if h_in > avail_h:
            h_in = avail_h; w_in = h_in * im.size[0] / im.size[1]
        s.shapes.add_picture(grp[0], Inches(0.95 + (avail_w - w_in) / 2), Inches(y), width=Inches(w_in))


def run(model_path, out_path, title, subtitle, note, img_dir, brand=None):
    global OUT, IMG_PPT
    OUT = os.path.dirname(model_path)
    IMG_PPT = img_dir
    book = json.load(open(model_path, encoding="utf-8"))
    prep_images()
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    cover(prs, title, subtitle, note)
    for ci, c in enumerate(book, 1):
        count = sum(len(g["questions"]) for s in c["sections"] for g in s["groups"])
        if count:
            chapter(prs, ci, c["title"], count)
        for sec in c["sections"]:
            ans = sec.get("ans") or {}
            if sec.get("net_files"):
                net_slides(prs, sec["net_files"], f"{c['title']}　{sec['title']}", c["title"])
            for g in sec["groups"]:
                for q in g["questions"]:
                    head = f"原书 P{q['page']:03d}" if q.get("page") else sec["title"]
                    question_slides(prs, q, head, f"{c['title']}　{sec['title']}")
                    a = {}
                    letter = (ans.get("choice") or {}).get(q["no"]) if q.get("options") else None
                    if letter:
                        otxt = next((t for ch, t in (q.get("options") or []) if ch == letter), "")
                        a = {"text": f"{letter}" + (f"　{otxt}" if otxt else "")}
                    if not a:
                        comp = (ans.get("comp") or {}).get(q["no"])
                        if comp:
                            a = {"text": "\n".join(comp)}
                    answer_slides(prs, q, a, head, f"{c['title']}　{sec['title']}")
    brand_slide(prs, brand)
    prs.save(out_path)
    return out_path
