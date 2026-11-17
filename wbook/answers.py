"""Parse answer keys (七年级 / 八年级) from the MinerU markdown into per-section answers."""
import re, json, sys, os

SEC_RE = re.compile(r"^(第[一二三四五六七八九十]+[节章]|综合(检测|练习)[（(]?[一二三四5]?[）)]?)[\s　]*(.*)$")


def clean(t):
    t = t.replace("　", " ")
    t = re.sub(r" {2,}", lambda m: "_" * min(10, max(4, len(m.group(0)))), t)
    t = re.sub(r" +", " ", t)
    return t.strip()


def parse_tables(frag):
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", frag, re.S):
        cells = [clean(re.sub(r"<[^>]+>", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        rows.append(cells)
    return rows


def parse(path):
    raw = open(path, encoding="utf-8").read()
    raw = re.sub(r"<eq>(.*?)</eq>", r"\1", raw)
    lines = raw.split("\n")
    out = []          # ordered list of {title, choice:{}, comp:{}}
    cur = None
    mode = None
    qno = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line.startswith("<table>"):
            buf = line
            while "</table>" not in buf and i < len(lines):
                buf += lines[i]; i += 1
            rows = parse_tables(buf)
            if cur is not None:
                nums = None
                for r in rows:
                    cells = [c for c in r if c]
                    if not cells:
                        continue
                    if all(re.fullmatch(r"\d{1,2}", c) for c in cells) and len(cells) >= 3:
                        nums = cells
                    elif all(re.fullmatch(r"[A-D×√]+", c) for c in cells) and nums:
                        for a, b in zip(nums, cells):
                            cur["choice"][a] = b
                        nums = None
            continue
        if line.startswith("!["):
            continue
        line = re.sub(r"!\[image\]\([^)]*\)", "", line)
        t = clean(re.sub(r"^#+\s*", "", line))
        m = re.match(r"^(第[一二三四五六七八九十]+[节章])\s*(.*)$", t)
        if m and len(t) < 40:
            cur = {"title": m.group(1) + (" " + m.group(2) if m.group(2) else ""), "choice": {}, "comp": {}}
            out.append(cur); mode = None; qno = None
            continue
        m = re.match(r"^(综合(检测|练习)[（(]?\s*[一二三四五六七八九十\d]?\s*[）)]?)$", t)
        if m and len(t) < 20:
            cur = {"title": t, "choice": {}, "comp": {}}
            out.append(cur); mode = None; qno = None
            continue
        if re.match(r"^[一二三]、\s*选择题", t):
            mode = "choice"; continue
        if re.match(r"^[一二三]、\s*综合题", t):
            mode = "comp"; qno = None; continue
        if cur is None:
            continue
        if mode == "comp":
            m = re.match(r"^(\d{1,2})\s*[.．、]?\s*(.*)$", t)
            if m and (m.group(2) == "" or re.match(r"^[（(]?\s*\d", m.group(2)) or "分" in m.group(2)[:8]):
                qno = m.group(1)
                cur["comp"].setdefault(qno, [])
                rest = m.group(2).strip()
                if re.match(r"^[（(]\s*\d", rest):
                    cur["comp"][qno].append(clean(rest))
                continue
            if qno is not None:
                cur["comp"][qno].append(t)
    return out


def summarize(items, label):
    print(f"=== {label}: {len(items)} sections")
    for it in items:
        print(f"  {it['title'][:26]:28s} 选择{len(it['choice']):>3} 综合{len(it['comp']):>2} "
              f"{sorted(it['choice'].items())[:3]}")
