"""Shared PDF layout helpers: run pdftohtml -xml, parse into page -> lines/images."""
import re, html, subprocess, os, glob

def run_xml(pdf, first=None, last=None, out_dir=None):
    out_dir = out_dir or "/tmp/pdfxml"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, "x")
    cmd = ["pdftohtml", "-xml", "-q", "-c"]
    if first: cmd += ["-f", str(first)]
    if last: cmd += ["-l", str(last)]
    cmd += [pdf, base]
    subprocess.run(cmd, check=True, capture_output=True)
    return base + ".xml"

def parse(xml_path):
    raw = open(xml_path, encoding="utf-8").read()
    fonts = {}
    for m in re.finditer(r'<fontspec id="(\d+)" size="([\d.]+)" family="([^"]*)" color="([^"]*)"', raw):
        fonts[m.group(1)] = {"size": float(m.group(2)), "family": m.group(3), "color": m.group(4)}
    pages = []
    for pm in re.finditer(r'<page ([^>]*)>(.*?)</page>', raw, re.S):
        pa = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(1)))
        no = int(pa.get("number", 0)); W = int(float(pa.get("width", 812))); H = int(float(pa.get("height", 1131)))
        body = pm.group(2)
        lines = []; images = []
        for tm in re.finditer(r'<text ([^>]*?)>(.*?)</text>', body, re.S):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', tm.group(1)))
            txt = html.unescape(re.sub(r"<[^>]+>", "", tm.group(2)))
            f = fonts.get(attrs.get("font"), {"size": 10.0})
            lines.append({
                "top": float(attrs.get("top", 0)), "left": float(attrs.get("left", 0)),
                "w": float(attrs.get("width", 0)), "h": float(attrs.get("height", 0)),
                "size": f["size"], "family": f.get("family", ""), "text": txt,
            })
        for im in re.finditer(r'<image ([^>]*?)/>', body):
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', im.group(1)))
            images.append({
                "top": float(attrs.get("top", 0)), "left": float(attrs.get("left", 0)),
                "w": float(attrs.get("width", 0)), "h": float(attrs.get("height", 0)),
                "src": attrs.get("src", ""),
            })
        pages.append({"no": no, "W": W, "H": H, "lines": lines, "images": images})
    return pages

def _cjk(ch):
    return "一" <= ch <= "鿿" or "　" <= ch <= "〿" or "＀" <= ch <= "￯"

def merge_lines(lines, tol=5.0):
    """Cluster raw text runs into visual lines by vertical centre (handles superscripts)."""
    els = [e for e in lines if e["text"].strip()]
    els.sort(key=lambda e: (e["top"], e["left"]))
    out = []
    for el in els:
        h = max(el["h"], 14.0)
        cy = el["top"] + h / 2.0
        best, bestd = None, tol
        for ln in out:
            d = abs(ln["_cy"] - cy)
            if d > bestd or el["left"] < ln["left"] - 2 or abs(ln["size"] - el["size"]) > 2.5:
                continue
            gap = el["left"] - ln["right"]
            if gap > 40 and not re.fullmatch(r"[（(][\s\u3000]{0,8}[）)]", el["text"].strip()):
                continue           # side-by-side column: keep as a separate line
            best, bestd = ln, d
        if best is not None:
            gap = el["left"] - best["right"]
            sep = ""
            if gap > 6:
                sep = " "
            prev = best["text"][-1:] if best["text"] else ""
            nxt = el["text"][:1]
            if sep and prev and nxt and _cjk(prev) and _cjk(nxt):
                sep = ""
            best["text"] = best["text"] + sep + el["text"].strip()
            best["left"] = min(best["left"], el["left"])
            best["right"] = max(best["right"], el["left"] + el["w"])
            best["size"] = max(best["size"], el["size"])
        else:
            out.append({"top": el["top"], "left": el["left"], "right": el["left"] + el["w"],
                        "h": el["h"], "size": el["size"], "family": el.get("family", ""),
                        "text": el["text"].strip(), "_cy": cy})
    out.sort(key=lambda l: (l["top"], l["left"]))
    for l in out:
        l["w"] = l["right"] - l["left"]
        l.pop("_cy", None)
    return out

_SIZES = {}


def pt_per_xml(pdf):
    """pt per xml-pixel; pdftohtml renders every page to an 812px-wide canvas."""
    if pdf not in _SIZES:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        m = re.search(r"Page size:\s+([\d.]+) x ([\d.]+)", out)
        _SIZES[pdf] = (float(m.group(1)), float(m.group(2))) if m else (595.0, 842.0)
    return _SIZES[pdf][0] / 812.0


def crop(pdf, page_no, box, out_png, dpi=200):
    """box = (left, top, right, bottom) in xml px."""
    from PIL import Image
    sc = dpi / 72.0
    k = pt_per_xml(pdf)
    px = [v * k * sc for v in box]
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no),
                    "-x", str(int(px[0])), "-y", str(int(px[1])),
                    "-W", str(max(1, int(px[2] - px[0]))), "-H", str(max(1, int(px[3] - px[1]))),
                    pdf, "/tmp/_crop"], check=True, capture_output=True)
    files = sorted(glob.glob("/tmp/_crop*.png"))
    if not files:
        return False
    im = Image.open(files[0]).convert("RGB")
    im.save(out_png)
    for f in files:
        os.remove(f)
    return True
