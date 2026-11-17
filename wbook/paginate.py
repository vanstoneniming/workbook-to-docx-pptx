"""八年级: assign printed page numbers to questions, then locate figure boxes on pages."""
import re, sys, os, json
from . import pdfxml

PDF = None
BOOK = None
OUT = None
PAGE_OFFSET = 4
BODY_TOP, BODY_BOT = 140, 1042
LINE_H = 31.0
TOP, BOT = 5, 75          # printed page range


def is_bar(im):
    return 150 < im["w"] < 210 and im["h"] < 32


def page_figures(pg):
    out = []
    for im in pg["images"]:
        if is_bar(im) or im["w"] < 25 or im["h"] < 20:
            continue
        if im["h"] < 40 and im["w"] / max(im["h"], 1) > 6:
            continue
        if im["h"] < 120 and im["w"] / max(im["h"], 1) > 3.5:   # decorative section banner
            continue
        out.append([im["left"], im["top"], im["left"] + im["w"], im["top"] + im["h"]])
    out.sort(key=lambda b: (b[1], b[0]))
    return out


def merge_boxes(boxes, gap=14):
    merged = []
    for b in boxes:
        for m in merged:
            if not (b[2] < m[0] - gap or b[0] > m[2] + gap or b[3] < m[1] - gap or b[1] > m[3] + gap):
                m[0] = min(m[0], b[0]); m[1] = min(m[1], b[1])
                m[2] = max(m[2], b[2]); m[3] = max(m[3], b[3])
                break
        else:
            merged.append(list(b))
    return merged


def greedy_bars(sections, bars):
    """Give each section the next 2-3 bars that start on (or just after) its page."""
    out = []
    i = 0
    for sec in sections:
        start = sec["page"]
        if i >= len(bars):
            out.append(None); continue
        group = [bars[i]]
        j = i + 1
        while j < len(bars) and len(group) < 3:
            if bars[j][0] - PAGE_OFFSET > start + 2:
                break
            group.append(bars[j]); j += 1
        i = j
        out.append((group[0], group[-1], len(group), group[1] if len(group) > 2 else group[0]))
    return out


def match_bars(sections, bars):
    """DP: give each section 2 or 3 consecutive bars, minimising page mismatch."""
    n, m = len(sections), len(bars)
    INF = 10 ** 9
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for i in range(n):
        start = sections[i]["page"]
        for j in range(m + 1):
            if dp[i][j] >= INF:
                continue
            for k in (3, 2):
                if j + k > m:
                    continue
                cost = abs((bars[j][0] - PAGE_OFFSET) - start)
                if k == 3:
                    cost += abs((bars[j + 1][0] - PAGE_OFFSET) - start) * 0.3
                else:
                    cost += 3
                if dp[i + 1][j + k] > dp[i][j] + cost:
                    dp[i + 1][j + k] = dp[i][j] + cost
                    back[i + 1][j + k] = (j, k)
    best = min(range(m + 1), key=lambda j: dp[n][j])
    assign = []
    j = best
    for i in range(n, 0, -1):
        j0, k = back[i][j]
        assign.append((j0, k))
        j = j0
    assign.reverse()
    return [(bars[j0], bars[j0 + k - 1]) for j0, k in assign]


def est_lines(q):
    lead = len(q.get("lead", ""))
    stem = sum(len(x) for x in q["stem"])
    opts = sum(len(o[1]) for o in q["options"])
    subs = sum(len(x) for s in q["subs"] for x in s["text"])
    n = (lead + stem + subs) / 32.0 + opts / 52.0 + len(q["subs"]) * 0.6
    return max(2.0, n + 0.8)


def run(pdf_path, book_json, out_json, page_offset=4):
    global PDF, BOOK, OUT, PAGE_OFFSET
    PDF, BOOK, OUT, PAGE_OFFSET = pdf_path, book_json, out_json, page_offset
    chs = json.load(open(BOOK, encoding="utf-8"))
    xml = pdfxml.run_xml(PDF, out_dir="/tmp/wbook_xml_" + str(os.getpid()))
    pages = pdfxml.parse(xml)
    by_page = {p["no"]: p for p in pages}
    bars = sorted([(p["no"], im["top"]) for p in pages for im in p["images"] if is_bar(im)])
    sections = [s for c in chs for s in c["sections"]]
    graded = [s for s in sections if not s.get("exam")]
    asg = greedy_bars(graded, bars)
    for s, grp in zip(graded, asg):
        if grp is None:
            s["_test_page"] = s["page"]; s["_test_y"] = BODY_TOP; continue
        b0, b1, k, bmid = grp
        s["_test_page"] = b1[0] - PAGE_OFFSET
        s["_test_y"] = b1[1]
        if k == 3:
            if bmid[0] == b1[0]:
                s["net"] = {"items": [{"pdf_page": bmid[0], "box": [92, bmid[1] + 26, 745, b1[1] - 8]}]}
            else:
                items = [{"pdf_page": bmid[0], "box": [92, bmid[1] + 26, 745, BODY_BOT]}]
                for pp in range(bmid[0] + 1, b1[0]):
                    items.append({"pdf_page": pp, "box": [92, BODY_TOP, 745, BODY_BOT]})
                if b1[1] > BODY_TOP + 60:
                    items.append({"pdf_page": b1[0], "box": [92, BODY_TOP, 745, b1[1] - 8]})
                s["net"] = {"items": items}
        elif k == 2 and b0[0] == b1[0] and b1[1] - b0[1] > 140:
            s["net"] = {"items": [{"pdf_page": b0[0], "box": [92, b0[1] + 26, 745, b1[1] - 8]}]}
    for s in sections:
        if s.get("exam"):
            s["_test_page"] = s["page"]
            s["_test_y"] = BODY_TOP
        print(f"{s['title'][:22]:24s} 目录p{s['page']:>2}  检测p{s['_test_page']:>2} y={s['_test_y']:.0f}")
    # page ranges
    for i, s in enumerate(sections):
        nxt = sections[i + 1]["page"] if i + 1 < len(sections) else 77
        s["_end_page"] = nxt - 1
    # figure boxes per page
    figs_by_page = {}
    import vecfig
    for pno, pg in by_page.items():
        b = merge_boxes(page_figures(pg), gap=3)
        if len(b) < 3:
            try:
                arr = vecfig.render(PDF, pno, 120)
                vb = [v for v in vecfig.graphics_boxes(arr)
                      if (v[3] - v[1]) > 45 and (v[2] - v[0]) > 90
                      and not ((v[3] - v[1]) < 120 and (v[2] - v[0]) / max(1.0, v[3] - v[1]) > 3.5)]
                for v in vb:
                    if not any(abs(v[1] - x[1]) < 25 and abs(v[0] - x[0]) < 30 for x in b):
                        b.append(v)
            except Exception:
                pass
        if b:
            figs_by_page[pno - PAGE_OFFSET] = sorted(b, key=lambda x: (x[1], x[0]))
    # distribute
    for s in sections:
        qs = [q for g in s["groups"] for q in g["questions"]]
        if not qs:
            continue
        p0, p1 = s["_test_page"], s["_end_page"]
        caps = []
        for p in range(p0, p1 + 1):
            avail = (BODY_BOT - (s["_test_y"] if p == p0 else BODY_TOP)) / LINE_H
            for fb in figs_by_page.get(p, []):
                avail -= (fb[3] - fb[1]) / LINE_H + 0.8
            caps.append(max(4.0, avail))
        total_cap = sum(caps)
        ests = [est_lines(q) for q in qs]
        total_est = sum(ests)
        scale = total_cap / total_est if total_est else 1
        idx, used, page = 0, 0.0, 0
        for q, e in zip(qs, ests):
            e *= scale
            if used + e > caps[page] + 1.5 and page < len(caps) - 1:
                page += 1; used = 0.0
            q["page"] = p0 + page
            used += e
        # figures: map the section's figure refs (document order) onto the section's
        # figure boxes (page order) -- robust against off-by-one page estimates
        boxes_seq = []
        for p in range(p0, p1 + 1):
            for bx in figs_by_page.get(p, []):
                boxes_seq.append((p, bx))
        figs_seq = [(q, fr) for q in qs for fr in q["figs"]]
        if boxes_seq and figs_seq:
            nb, nf = len(boxes_seq), len(figs_seq)
            for i, (q, fr) in enumerate(figs_seq):
                bi = i if nf == nb else round(i * (nb - 1) / max(1, nf - 1))
                bi = min(max(bi, 0), nb - 1)
                p_, bx_ = boxes_seq[bi]
                fr["pdf_page"] = p_ + PAGE_OFFSET
                fr["box"] = bx_
    for c in chs:
        for s in c["sections"]:
            s.pop("_test_y", None)
    json.dump(chs, open(OUT, "w"), ensure_ascii=False, indent=1)
    tot = sum(len(g["questions"]) for c in chs for s in c["sections"] for g in s["groups"])
    miss = sum(1 for c in chs for s in c["sections"] for g in s["groups"] for q in g["questions"]
               if any("box" not in f for f in q["figs"]))
    print("questions", tot, "figs without box", miss)
