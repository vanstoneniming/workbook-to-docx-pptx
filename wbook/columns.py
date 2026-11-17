"""Reorder side-by-side text columns so two-column cards are read column-wise."""


def _overlap(a, b):
    top = max(a["top"], b["top"])
    bot = min(a["top"] + max(a["h"], 14), b["top"] + max(b["h"], 14))
    return max(0.0, bot - top)


def _side_by_side(a, b, gap=40.0):
    if _overlap(a, b) < 6:
        return False
    ra = a["left"] + a["w"]
    rb = b["left"] + b["w"]
    return ra < b["left"] - gap or rb < a["left"] - gap


def reorder_columns(lines, gap=40.0):
    """L,R,L,R… 交替的双栏卡片，改成整栏读完再读右栏。"""
    n = len(lines)
    out = []
    i = 0
    while i < n:
        if i + 1 < n and _side_by_side(lines[i], lines[i + 1], gap):
            left = [lines[i]]
            right = [lines[i + 1]]
            j = i + 2
            while j + 1 < n and _side_by_side(lines[j], lines[j + 1], gap):
                a, b = lines[j], lines[j + 1]
                if a["left"] <= b["left"]:
                    left.append(a); right.append(b)
                else:
                    left.append(b); right.append(a)
                j += 2
            if len(left) + len(right) >= 3:
                out.extend(left)
                out.extend(right)
                i = j
                continue
        out.append(lines[i])
        i += 1
    return out
