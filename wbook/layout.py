"""Shared layout helpers: split question text into body / ①②③④ items / options rows."""
import re

ITEM_CHARS = "①②③④⑤⑥⑦⑧⑨⑩"
ITEM_RE = re.compile(r"^([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)$")
BRACKET_RE = re.compile(r"[（(]\s*[_＿　 ]*\s*[）)]")


def nbsp_bracket(text):
    """Keep （　　） on one line: use non-breaking spaces inside the brackets."""
    return BRACKET_RE.sub("（  ）", text)


def cjk_len(s):
    n = 0.0
    for ch in s:
        if ch == " ":
            n += 1.0
        elif ord(ch) > 127:
            n += 1.0
        else:
            n += 0.55
    return n


def est_lines(text, width_in, pt):
    per = max(1.0, width_in * 72 / max(pt, 6))
    n = 0
    for ln in str(text).split("\n"):
        n += max(1, int(-(-cjk_len(ln) // per)) if cjk_len(ln) > per else 1)
    return n


def split_stem(lines):
    """stem 行 → (正文行, ①②③④ 条目列表)。"""
    body, items = [], []
    for ln in lines:
        s = str(ln).strip()
        if not s:
            continue
        n_item = sum(1 for ch in s if ch in ITEM_CHARS)
        if n_item >= 2 and s[0] in ITEM_CHARS:
            parts = [p.strip() for p in re.split(r"(?=[" + ITEM_CHARS + r"])", s) if p.strip()]
            items.extend(parts)
        elif ITEM_RE.match(s):
            items.append(s)
        else:
            body.append(s)
    return body, items


def choose_cols(texts, width_in, pt, max_cols=4):
    """按最长条目和可用宽度决定每行放几个。"""
    if not texts:
        return 1
    longest = max(cjk_len(t) for t in texts)
    budget = width_in * 72 / max(pt, 6)
    per_gap = 2.0
    for cols in (4, 2, 1):
        if cols > max_cols or cols > len(texts):
            continue
        if cols == 4 and longest > budget / 4 - per_gap:
            continue
        if cols == 2 and longest > budget / 2 - per_gap:
            continue
        return cols
    return 1


def rows_of(texts, cols):
    return [texts[i:i + cols] for i in range(0, len(texts), cols)]


def option_texts(q):
    return [f"{c}. {t}" for c, t in (q.get("options") or [])]


def layout_question(q, width_in, body_pt, opt_pt, sub_pt):
    """返回 [(kind, payload, height_in)]，kind ∈ body/item/option/sub。"""
    out = []
    body, items = split_stem(q.get("stem") or [])
    lead = q.get("lead") or ""
    if lead:
        lh = est_lines(nbsp_bracket(lead), width_in, body_pt) * body_pt * 1.32 * 1.12 / 72
        out.append(("lead", nbsp_bracket(lead), lh))
    for p in body:
        p = nbsp_bracket(p)
        h = est_lines(p, width_in, body_pt) * body_pt * 1.32 * 1.12 / 72
        out.append(("body", p, h))

    if items:
        cols = choose_cols(items, width_in, opt_pt)
        for row in rows_of(items, cols):
            hh = max(est_lines(t, width_in / cols - 0.12, opt_pt) for t in row) * opt_pt * 1.3 * 1.12 / 72
            out.append(("row", (row, cols), hh))
    opts = option_texts(q)
    if opts:
        cols = choose_cols(opts, width_in, opt_pt)
        for row in rows_of(opts, cols):
            hh = max(est_lines(t, width_in / cols - 0.12, opt_pt) for t in row) * opt_pt * 1.3 * 1.12 / 72
            out.append(("row", (row, cols), hh))
    for sub in q.get("subs") or []:
        txt = nbsp_bracket(f"（{sub['no']}）" + "".join(sub["text"]))
        h = est_lines(txt, width_in, sub_pt) * sub_pt * 1.3 * 1.12 / 72
        out.append(("sub", txt, h))
    return out


def measure(blocks):
    return sum(b[2] for b in blocks)
