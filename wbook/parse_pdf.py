"""七年级 book: build structured content from the PDF text layer (no OCR)."""
import re, sys, os, json
from . import pdfxml, columns

PDF = None
PAGE_OFFSET = 4
HEADER_ZONE = 110


def run(pdf_path, page_offset=4, header_zone=110):
    """有文本层的 PDF → 章节结构（不 OCR）。"""
    global PDF, PAGE_OFFSET, HEADER_ZONE
    PDF, PAGE_OFFSET, HEADER_ZONE = pdf_path, page_offset, header_zone
    pages = pdfxml.parse(pdfxml.run_xml(PDF))
    return build(pages)

CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十]+章")
SECTION_RE = re.compile(r"^第[一二三四五六七八九十]+节")
TEST_RE = re.compile(r"^综合(检测|练习|测试)[（(]?\s*[一二三四五六七八九十\d]")
GROUP_RE = re.compile(r"^([一二三四五六七八九])\s*[、.．]\s*(.+)$")
PART_RE = re.compile(r"^第[一二]部分")
QNUM_RE = re.compile(r"^(\d{1,2})\s*[.．]\s*(.*)$")
SUBQ_RE = re.compile(r"^[（(]\s*(\d{1,2})\s*[）)]\s*(.*)$")
OPT_RE = re.compile(r"^([A-D])\s*[.．、]\s*")
CAPTION_RE = re.compile(r"^图\s*\d+\s*[-—－]\s*\d+")
LBL_NET = re.compile(r"^知\s*识\s*网\s*络$")
LBL_GOAL = re.compile(r"^学\s*习\s*目\s*标$")
LBL_TEST = re.compile(r"^学\s*习\s*检\s*测$")


def norm(t):
    t = t.replace("\u3000", " ")
    t = re.sub(r"(\d)\s*[~～]\s*(\d)", r"\1~\2", t)
    t = re.sub(r" {2,}", lambda m: "_" * min(10, max(4, len(m.group(0)))), t)
    t = re.sub(r" +", " ", t)
    t = re.sub(r"（\s*）", "（　　）", t)
    return t.strip()


def split_options(t):
    """'A. xx B. yy C. zz D. ww' -> [['A','xx'],...] ; also handles single-space joins."""
    marks = []
    for m in re.finditer(r"([A-D])\s*[.．、]\s*", t):
        ch, s, e = m.group(1), m.start(), m.end()
        if s > 0 and re.match(r"[A-Za-z0-9]", t[s - 1]):
            continue
        marks.append((ch, s, e))
    if not marks:
        return []
    seq = list(marks)
    if not seq:
        return []
    if len(seq) == 1 and marks[0][1] > 0:
        return []
    out = []
    for i, (ch, s, e) in enumerate(seq):
        end = seq[i + 1][1] if i + 1 < len(seq) else len(t)
        txt = re.sub(r"^_+|_+$", "", t[e:end].strip()).strip()
        out.append([ch, txt])
    return out


def cluster_figures(pg, gap=18.0):
    items = []
    for im in pg["images"]:
        if im["w"] < 12 or im["h"] < 10:
            continue
        if im["h"] < 40 and im["w"] / max(im["h"], 1) > 6:   # grey label bar / rule
            continue
        items.append([im["left"], im["top"], im["left"] + im["w"], im["top"] + im["h"]])
    for l in pg["lines"]:
        t = norm(l["text"])
        if not t or l["top"] <= HEADER_ZONE:
            continue
        if l["size"] < 16.0 and not CAPTION_RE.match(t):
            items.append([l["left"], l["top"], l["left"] + l["w"], l["top"] + max(l["h"], 14)])
    n = len(items)
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            a, b = items[i], items[j]
            if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                union(i, j)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    boxes = []
    for g in groups.values():
        x0 = min(i[0] for i in g); y0 = min(i[1] for i in g)
        x1 = max(i[2] for i in g); y1 = max(i[3] for i in g)
        if (x1 - x0) < 40 or (y1 - y0) < 30:
            continue
        boxes.append([x0, y0, x1, y1])
    boxes.sort(key=lambda b: (b[1], b[0]))
    merged = []
    for b in boxes:
        for m in merged:
            if not (b[2] < m[0] - 4 or b[0] > m[2] + 4 or b[3] < m[1] - 4 or b[1] > m[3] + 4):
                m[0] = min(m[0], b[0]); m[1] = min(m[1], b[1])
                m[2] = max(m[2], b[2]); m[3] = max(m[3], b[3])
                break
        else:
            merged.append(list(b))
    return merged


def _grow_net(net, pg, line):
    items = net["items"]
    box = None
    for it in items:
        if it["pdf_page"] == pg["no"]:
            box = it["box"]; break
    def grow(x0, y0, x1, y1):
        nonlocal box
        if box is None:
            box = [x0, y0, x1, y1]; items.append({"pdf_page": pg["no"], "box": box})
        else:
            box[0] = min(box[0], x0); box[1] = min(box[1], y0)
            box[2] = max(box[2], x1); box[3] = max(box[3], y1)
    if line is not None:
        grow(line["left"], line["top"], line["left"] + line["w"], line["top"] + max(line["h"], 14))
    else:
        y0 = min((it["box"][1] for it in items if it["pdf_page"] == pg["no"]), default=0)
        for im in pg["images"]:
            if im["w"] < 12 or im["h"] < 10:
                continue
            if 150 < im["w"] < 210 and im["h"] < 32:
                continue
            if im["top"] < y0 - 6:
                continue
            grow(im["left"], im["top"], im["left"] + im["w"], im["top"] + im["h"])


def build(pages):
    chapters = []
    cur_ch = cur_sec = group = q = None
    part = None            # "goal" | "net" | "test" | None
    lead = []              # material waiting for next question
    net_start = None
    for pg in pages:
        printed = pg["no"] - PAGE_OFFSET
        lines = columns.reorder_columns([l for l in pdfxml.merge_lines(pg["lines"]) if l["top"] > HEADER_ZONE])
        # 大块底色/卡片图：它上面的文字属于图本身（设计版式），不进正文流
        panels = []
        for im in pg["images"]:
            if im["w"] >= 380 and im["h"] >= 180:
                panels.append([im["left"], im["top"], im["left"] + im["w"], im["top"] + im["h"]])
        if panels:
            kept = []
            for l in lines:
                cx = l["left"] + l["w"] / 2
                cy = l["top"] + max(l["h"], 14) / 2
                if any(b[0] - 4 <= cx <= b[2] + 4 and b[1] - 4 <= cy <= b[3] + 4 for b in panels):
                    continue
                kept.append(l)
            lines = kept
        figs = cluster_figures(pg)
        for b in panels:
            if not any(abs(b[1] - f[1]) < 20 and abs(b[0] - f[0]) < 20 for f in figs):
                figs.append(list(b))

        figs.sort(key=lambda b: (b[1], b[0]))
        panel_set = []
        for b in panels:
            panel_set.append(b)
        page_qs = []
        opt_left = None
        for l in lines:
            t = norm(l["text"])
            if not t:
                continue
            small = l["size"] < 16.0
            if not small:
                if CHAPTER_RE.match(t) and l["size"] >= 22:
                    cur_ch = {"title": t, "page": printed, "sections": []}
                    chapters.append(cur_ch)
                    cur_sec = group = q = None; part = None; lead = []
                    continue
                if TEST_RE.match(t) and l["size"] >= 22:
                    cur_ch = {"title": "综合检测", "page": printed, "sections": []}
                    chapters.append(cur_ch)
                    cur_sec = {"title": t, "page": printed, "groups": []}
                    cur_ch["sections"].append(cur_sec)
                    group = q = None; part = "test"; lead = []
                    continue
                if SECTION_RE.match(t) and l["size"] >= 19:
                    if cur_ch is None:
                        cur_ch = {"title": "", "page": printed, "sections": []}
                        chapters.append(cur_ch)
                    cur_sec = {"title": t, "page": printed, "groups": []}
                    cur_ch["sections"].append(cur_sec)
                    group = q = None; part = None; lead = []
                    continue
                if LBL_TEST.match(t):
                    if part == "net" and net_start is not None:
                        cur_sec["net"] = net_start; net_start = None
                    part = "test"; group = q = None; continue
                if LBL_GOAL.match(t):
                    part = "goal"; group = q = None; continue
                if LBL_NET.match(t):
                    part = "net"; group = q = None
                    net_start = {"page": printed, "items": []}
                    _grow_net(net_start, pg, {"left": 88, "top": l["top"] + 30, "w": 660,
                                              "h": max(l["h"], 14)})
                    continue
                if PART_RE.match(t) and cur_sec is not None and part == "test":
                    group = {"label": t, "questions": []}
                    cur_sec["groups"].append(group); q = None; continue
                m = GROUP_RE.match(t)
                if m and l["left"] < 240 and part == "test":
                    group = {"label": t, "questions": []}
                    cur_sec["groups"].append(group); q = None; continue
                m = QNUM_RE.match(t)
                if m and group is not None and part == "test" and l["left"] < 240:
                    q = {"no": m.group(1), "page": printed, "lead": "", "stem": [m.group(2).strip()],
                         "options": [], "subs": [], "figures": [], "_top": l["top"]}
                    if lead:
                        q["lead"] = " ".join(lead); lead = []
                    group["questions"].append(q)
                    page_qs.append((l["top"], q))
                    opt_left = None
                    continue
            if part == "net":
                _grow_net(net_start, pg, l)
                continue
            if part != "test" or q is None:
                if not small and part == "test":
                    lead.append(t)
                continue
            if small:
                continue
            m = SUBQ_RE.match(t)
            if m:
                q["subs"].append({"no": m.group(1), "text": [m.group(2).strip()]})
                opt_left = None
                continue
            if OPT_RE.match(t) and not q["subs"]:
                got = split_options(t)
                if got:
                    q["options"].extend(got)
                    if opt_left is None:
                        opt_left = l["left"]
                    continue
            if q["options"] and l["left"] >= (opt_left or 999) - 6:
                q["options"][-1][1] += t      # wrapped option line
                continue
            if q["subs"]:
                q["subs"][-1]["text"].append(t)
            elif q["options"]:
                lead.append(t)                # material for the next question
            else:
                q["stem"].append(t)
        if part == "net" and net_start is not None:
            _grow_net(net_start, pg, None)
        # --- figure assignment: caption number first, position as fallback ---
        caps = []
        for l in pg["lines"]:
            t = norm(l["text"])
            if CAPTION_RE.match(t) or re.search(r"图\s*\d+\s*[-—－]\s*\d+", t):
                for m in re.finditer(r"图\s*(\d+)\s*[-—－]\s*(\d+)", t):
                    caps.append((f"图{m.group(1)}-{m.group(2)}", l["left"], l["top"]))
        for box in figs:
            cy = (box[1] + box[3]) / 2.0
            num = None
            best = 1e9
            for key, cx, ctop in caps:
                dy = min(abs(ctop - box[3]), abs(box[1] - ctop))
                dx = abs(cx - (box[0] + box[2]) / 2)
                if dy < 55 and dx < (box[2] - box[0]) / 2 + 90:
                    score = dy * 2 + dx * 0.15
                    if score < best:
                        best, num = score, key
            if num:
                for top, qq in page_qs:
                    raw = norm(qq.get("lead", "")) + " " + " ".join(qq["stem"])
                    if num.replace("图", "") in raw.replace(" ", "").replace("图", "") or num in raw:
                        rec = {"pdf_page": pg["no"], "box": box, "cap": num}
                        if any(abs(box[0] - b[0]) < 12 and abs(box[1] - b[1]) < 12 for b in panels):
                            rec["panel"] = True
                        qq["figures"].append(rec)
                        num = "hit"
                        break
            if num == "hit":
                continue
            before = [(top, qq) for top, qq in page_qs if top <= cy]
            after = [(top, qq) for top, qq in page_qs if top > cy]
            target = None
            if before:
                target = before[-1][1]
            elif after:
                target = after[0][1]
            if target is not None:
                rec = {"pdf_page": pg["no"], "box": box, "cap": num}
                if any(abs(box[0] - b[0]) < 12 and abs(box[1] - b[1]) < 12 for b in panels):
                    rec["panel"] = True
                target["figures"].append(rec)
    return chapters
