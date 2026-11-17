"""八年级 book: MinerU markdown -> structure; page numbers by anchored estimation."""
import re, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

PDF = None
MD = None
CHAPTERS = []
EXAMS = []


def run(md_path, chapters, exams, pdf_path=None):
    """MinerU markdown → 章节结构；chapters/exams 来自配置里的目录页号表。"""
    global MD, PDF, CHAPTERS, EXAMS
    MD, PDF, CHAPTERS, EXAMS = md_path, pdf_path, chapters, exams
    return parse(load_md())


QNUM_RE = re.compile(r"^(\d{1,2})\s*[.．]\s*(.*)$")
SUBQ_RE = re.compile(r"^[（(]\s*(\d{1,2})\s*[）)]\s*(.*)$")
OPT_RE = re.compile(r"([A-D])\s*[.．、]\s*")
IMG_RE = re.compile(r"^!\[image\]\(([^)]+)\)")
GROUP_RE = re.compile(r"^([一二三四五六])\s*、\s*(.+)$")


def clean(t):
    t = t.replace("　", " ")
    t = re.sub(r"(\d)\s*[~～]\s*(\d)", r"\1~\2", t)
    t = re.sub(r" {2,}", lambda m: "_" * min(10, max(4, len(m.group(0)))), t)
    t = re.sub(r" +", " ", t)
    t = re.sub(r"（\s*_*\s*_*\s*）", "（　　）", t)
    t = re.sub(r"\(\s*_*\s*_*\s*\)", "(　　)", t)
    t = t.strip()
    if re.fullmatch(r"[（(]\s*[）)]", t):
        return ""
    return t


def split_options(t):
    marks = []
    for m in OPT_RE.finditer(t):
        s = m.start()
        if s > 0 and re.match(r"[A-Za-z0-9]", t[s - 1]):
            continue
        marks.append((m.group(1), s, m.end()))
    if not marks:
        return []
    seq = list(marks)
    if not seq:
        return []
    out = []
    for i, (ch, s, e) in enumerate(seq):
        end = seq[i + 1][1] if i + 1 < len(seq) else len(t)
        txt = re.sub(r"^_+|_+$", "", t[e:end].strip()).strip()
        out.append([ch, txt])
    return out


def pull_inline_options(q):
    """Options glued onto a stem line: '8. 我国 ... A. xx B. yy C. zz D. ww'."""
    newstem = []
    for ln in q["stem"]:
        opts = split_options(ln)
        if len(opts) >= 2 and not q["options"]:
            head = ln[:OPT_RE.search(ln).start()].strip() if OPT_RE.search(ln) else ""
            head = re.sub(r"[（(]\s*）$", "（　　）", head).strip()
            if head:
                newstem.append(head)
            q["options"].extend(opts)
        else:
            newstem.append(ln)
    q["stem"] = newstem
    return q


def table_to_rows(frag):
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", frag, re.S):
        cells = [clean(re.sub(r"<[^>]+>", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        rows.append(cells)
    return rows


def load_md():
    raw = open(MD, encoding="utf-8").read()
    raw = re.sub(r"<eq>(.*?)</eq>", lambda m: m.group(1), raw)
    raw = raw.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return raw.split("\n")


def make_skeleton():
    chapters, by_title = [], {}
    for ct, secs in CHAPTERS:
        ch = {"title": ct, "page": secs[0][1], "sections": []}
        chapters.append(ch)
        for st, pg in secs:
            sec = {"title": st, "page": pg, "groups": [], "net": None}
            ch["sections"].append(sec)
            by_title[st] = sec
    exam_ch = {"title": "综合练习", "page": 61, "sections": []}
    chapters.append(exam_ch)
    for et, pg in EXAMS:
        sec = {"title": et, "page": pg, "groups": [], "net": None, "exam": True}
        exam_ch["sections"].append(sec)
        by_title[et] = sec
    return chapters, by_title


def parse(lines):
    chapters, by_title = make_skeleton()
    cur_sec = None
    cur = None
    group = None
    q = None
    lead = []
    pend_figs = []
    prev_img = False
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line or set(line) <= {"-", " "}:
            continue
        if line.startswith("<table>"):
            buf = line
            while "</table>" not in buf and i < len(lines):
                buf += lines[i]; i += 1
            if cur_sec is not None and cur == "test" and group is not None:
                group.setdefault("tables", []).append(table_to_rows(buf))
            continue
        head = line.startswith("#")
        title = clean(re.sub(r"^#+\s*", "", line)) if head else clean(line)

        # --- section headings (exact-ish) ---
        hit = None
        for key, sec in by_title.items():
            if "…" in title or "..." in title:
                continue
            if title.startswith(key) and len(title) - len(key) <= 6:
                hit = sec; break
        if hit is not None:
            cur_sec = hit
            if cur_sec.get("_seen"):
                cur_sec = None          # duplicate heading (e.g. chapter title also a section)
            else:
                cur_sec["_seen"] = True
            cur = "test" if cur_sec.get("exam") else None
            group = None; q = None; lead = []; pend_figs = []
            continue
        if cur_sec is None:
            continue
        if re.fullmatch(r"学\s*习\s*检\s*测", title):
            cur = "test"; group = None; q = None; continue
        if re.fullmatch(r"学\s*习\s*目\s*标", title):
            cur = "goal"; group = None; q = None; continue
        if re.fullmatch(r"知\s*识\s*网\s*络", title):
            cur = "net"; group = None; q = None; continue
        if cur != "test":
            continue
        # --- 综合练习一 has no heading of its own ---
        if GROUP_RE.match(title) and "单项选择题" in title and not cur_sec.get("exam"):
            cur_sec = by_title["综合练习一"]
            cur = "test"
        m = GROUP_RE.match(title)
        if m and (len(title) < 80) and (head or "。" not in title[:3]):
            group = {"label": title, "questions": [], "tables": []}
            cur_sec["groups"].append(group); q = None; lead = []
            continue
        if line.startswith("!["):
            mm = IMG_RE.match(line)
            if mm and q is not None:
                (pend_figs if lead else q["figs"]).append({"src": mm.group(1)})
            prev_img = True
            continue
        # 图片下方 1 行短文字 = 图注（"2月份的西沙群岛" / "图 1-1"），不要混进材料正文
        if prev_img and len(title) <= 18 and not re.search(r"[。！？；：]$", title) \
                and not re.match(r"^(\d{1,2}[.．]|[A-D][.．、]|[①-⑩]|[（(])", title):
            if q is not None and not lead:
                if q["figs"]:
                    q["figs"][-1]["cap"] = title
            else:
                if pend_figs:
                    pend_figs[-1]["cap"] = title
            prev_img = False
            continue
        prev_img = False
        m = SUBQ_RE.match(title)
        if m and q is not None:
            q["subs"].append({"no": m.group(1), "text": [clean(m.group(2))]})
            continue
        m = QNUM_RE.match(title)
        if m and group is not None:
            q = {"no": m.group(1), "lead": "", "stem": [clean(m.group(2))],
                 "options": [], "subs": [], "figs": [], "page": None}
            if lead:
                q["lead"] = " ".join(lead); lead = []
            if pend_figs:
                q["figs"].extend(pend_figs); pend_figs = []
            group["questions"].append(q)
            continue
        if q is None:
            lead.append(title); continue
        # body line of a question
        opts = split_options(title)
        if opts and not q["subs"] and len(q["options"]) < 4:
            q["options"].extend(opts)
            continue
        if q["options"] and not q["subs"] and len(q["options"]) >= 2:
            if re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩]", title):
                q["stem"].append(title)
            else:
                lead.append(title)
            continue
        if q["subs"]:
            q["subs"][-1]["text"].append(title)
        else:
            q["stem"].append(title)
    for c in chapters:
        for sec in c["sections"]:
            for g in sec["groups"]:
                for q in g["questions"]:
                    pull_inline_options(q)
    return chapters
