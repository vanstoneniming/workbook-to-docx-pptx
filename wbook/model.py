"""Normalise both books into one model and crop all figures."""
import os, json, re, sys
from . import pdfxml, answers

OUT = None
FIG = None
BOOK_PDFS = {}
ANSWER_MDS = {}


def run(out_dir, book_pdfs, answer_mds):
    """裁图 + 并答案，产出 model<tag>.json。"""
    global OUT, FIG, BOOK_PDFS, ANSWER_MDS
    OUT, BOOK_PDFS, ANSWER_MDS = out_dir, book_pdfs, answer_mds
    FIG = os.path.join(OUT, "fig")
    os.makedirs(FIG, exist_ok=True)
    out = {}
    for tag in book_pdfs:
        book = build(tag)
        json.dump(book, open(os.path.join(OUT, f"model{tag}.json"), "w"), ensure_ascii=False, indent=1)
        out[tag] = book
    return out


def norm_title(t):
    t = re.sub(r"\s+", "", t)
    t = t.replace("（", "(").replace("）", ")")
    return t


def load_answers(answer_mds):
    path = os.path.join(OUT, "answers.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    data = {tag: answers.parse(md) for tag, md in answer_mds.items() if md}
    json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
    return data


def answer_index(ans_list):
    idx = {}
    for a in ans_list:
        key = norm_title(a["title"])
        idx[key] = a
    return idx


def crop_book(book, pdf, tag):
    d = os.path.join(FIG, tag)
    os.makedirs(d, exist_ok=True)
    n = 0
    for c in book:
        for s in c["sections"]:
            for gi, g in enumerate(s["groups"]):
                for q in g["questions"]:
                    if "figs" not in q:
                        q["figs"] = q.pop("figures", [])
                    keep = []
                    seen = set()
                    for fi, f in enumerate(q["figs"]):
                        if "box" not in f:
                            continue
                        b = f["box"]
                        key = (f["pdf_page"], round(b[0] / 6), round(b[1] / 6))
                        if key in seen:
                            continue
                        seen.add(key)
                        if (b[3] - b[1]) <= 112 and (b[2] - b[0]) >= 500 and b[1] < 215:
                            continue          # decorative section banner (「综合练习一」条)
                        path = os.path.join(d, f"f{n:04d}.png")
                        if not os.path.exists(path):
                            b = f["box"]
                            pdfxml.crop(pdf, f["pdf_page"],
                                        [b[0] - 4, b[1] - 6, b[2] + 4, b[3] + 5], path, dpi=190)
                        f["file"] = path
                        keep.append(f)
                        n += 1
                    q["figs"] = keep
    return n


def trim_white(path, pad=6):
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0)
    box = diff.getbbox()
    if box:
        x0, y0, x1, y1 = box
        x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
        x1 = min(im.width, x1 + pad); y1 = min(im.height, y1 + pad)
        im.crop((x0, y0, x1, y1)).save(path)


def crop_net(book, pdf, tag):
    d = os.path.join(FIG, tag + "_net")
    os.makedirs(d, exist_ok=True)
    for c in book:
        for s in c["sections"]:
            net = s.get("net")
            if not net:
                continue
            files = []
            for i, it in enumerate(net["items"]):
                b = it["box"]
                path = os.path.join(d, f"net_{len(files)}_{abs(hash((c['title'], s['title'], i))) % 99999}.png")
                if not os.path.exists(path):
                    pdfxml.crop(pdf, it["pdf_page"], [88, b[1] - 2, 748, b[3] + 6], path, dpi=170)
                    trim_white(path)
                files.append(path)
            s["net_files"] = files


CAP_TAIL = re.compile(r"\s*图\s*\d+\s*[-—－]\s*\d+\s*$")
CAP_ONLY = re.compile(r"^图\s*\d+\s*[-—－]\s*\d+$")
MATH_ENV = re.compile(r"\\begin\{[a-z]+\}.*?\\end\{[a-z]+\}", re.S)
MATH_INLINE = re.compile(r"\$\$?(.+?)\$\$?", re.S)


def _latex_inner(s):
    s = s.replace("~", " ")                       # LaTeX 非断空格
    s = s.replace("\\%", "%").replace("\\times", "×").replace("\\sim", "~")
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = re.sub(r"\^\s*\{?\\circ\}?", "°", s)
    s = s.replace("\\circ", "°")
    s = re.sub(r"\\(?:mathrm|text|mathbf|rm|bf)\s*\{([^{}]*)\}", r"\1", s)
    s = s.replace("\\,", "").replace("\\;", "").replace("\\!", "")
    s = re.sub(r"[{}]", "", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    return s.replace("$", "")


def tidy_text(t):
    """把 MinerU 带出来的 LaTeX 碎片（$30^{\circ}\mathrm{N}$、$20^{\circ}\mathrm{C}$）还原成 ° / ℃。"""
    t = str(t)
    if "\\" not in t and "$" not in t:
        return t.strip()
    t = MATH_ENV.sub("", t)
    t = MATH_INLINE.sub(lambda m: _latex_inner(m.group(1)), t)
    t = re.sub(r"\\(?:mathrm|text|mathbf|rm|bf)\s*\{([^{}]*)\}", r"\1", t)
    t = t.replace("\\left", "").replace("\\right", "")
    t = t.replace("\\circ", "°").replace("\\sim", "~").replace("\\%", "%")
    t = t.replace("\\{", "{").replace("\\}", "}")
    t = re.sub(r"[{}]", "", t)
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("$", "")
    t = re.sub(r"°\s*C\b", "℃", t)
    t = re.sub(r"(\d)\s*°\s*([NSEW])\b", r"\1°\2", t)
    t = re.sub(r"(\d)\s*~\s*(\d)", r"\1~\2", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


END_PUNCT = "。！？：；…”’」』"


def join_paragraphs(lines, min_len=14):
    out = []
    for ln in lines:
        ln = str(ln).strip()
        if not ln:
            continue
        if out and len(out[-1]) >= min_len and out[-1][-1] not in END_PUNCT \
                and not re.match(r"^[①-⑩（(A-D]", ln) and not re.match(r"^[①-⑩（(]", out[-1][:1]):
            out[-1] = out[-1] + ln
        else:
            out.append(ln)
    return out


def tidy_question(q):
    q["lead"] = CAP_TAIL.sub("", tidy_text(q.get("lead") or "")).strip()
    stem = []
    for ln in q.get("stem") or []:
        ln = tidy_text(ln)
        if CAP_ONLY.match(ln):
            continue
        if ln:
            stem.append(ln)
    q["stem"] = stem
    for sub in q.get("subs") or []:
        sub["text"] = join_paragraphs([tidy_text(x) for x in sub["text"] if str(x).strip()])
    opts = {}
    for c, t in q.get("options") or []:
        t = tidy_text(t)
        if t and c not in opts:
            opts[c] = t
    q["options"] = [[c, opts[c]] for c in sorted(opts)]
    q["stem"] = join_paragraphs([re.sub(r"^[…\.·]+", "", x).strip() for x in q["stem"] if x.strip()])
    q["lead"] = re.sub(r"^[…\.·]+", "", q["lead"]).strip()


def build(tag):
    book = json.load(open(os.path.join(OUT, f"book{tag}.json"), encoding="utf-8"))
    pdf = BOOK_PDFS[tag]
    crop_book(book, pdf, tag)
    crop_net(book, pdf, tag)
    ans = load_answers(ANSWER_MDS)
    idx = answer_index(ans[tag])
    NEXT_LEAD = re.compile(r"(据此|读图|结合.{0,8}资料|根据).{0,40}完成\s*\d+\s*[~～\-]\s*\d+\s*题")
    for c in book:
        for s in c["sections"]:
            for g in s["groups"]:
                for q in g["questions"]:
                    if "figs" not in q:
                        q["figs"] = q.pop("figures", [])
                    tidy_question(q)
                qs = g["questions"]
                BR = re.compile(r"[（(][\s\u00a0\u3000]*[）)]")
                for i, q in enumerate(qs[:-1]):
                    keep = []
                    for p_ in q["stem"]:
                        moved = False
                        m = BR.search(p_)
                        if m and NEXT_LEAD.search(p_[m.end():]) and len(p_[m.end():]) > 20:
                            nxt = qs[i + 1]
                            nxt["lead"] = (p_[m.end():].strip() + " " + (nxt.get("lead") or "")).strip()
                            nxt["lead"] = re.sub(r"^[…\.·]+", "", nxt["lead"]).strip()
                            keep.append(p_[:m.end()].strip())
                            moved = True
                        if not moved:
                            keep.append(p_)
                    q["stem"] = keep
            key = norm_title(s["title"])
            a = idx.get(key)
            if a is None:
                for k, v in idx.items():
                    if key in k or k in key:
                        a = v; break
            if a:
                a["comp"] = {k: [tidy_text(x) for x in v] for k, v in a.get("comp", {}).items()}
            s["ans"] = a or {"choice": {}, "comp": {}}
    return book
