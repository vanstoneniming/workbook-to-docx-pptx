"""Crop figures from a PDF page, expanding the box outward until a clean white margin."""
import os, subprocess, glob
import numpy as np
from PIL import Image

_CACHE = {}


def page_image(pdf, page_no, dpi=150):
    key = (pdf, page_no, dpi)
    if key in _CACHE:
        return _CACHE[key]
    for old in glob.glob("/tmp/_full*.png"):
        os.remove(old)
    subprocess.run(["pdftoppm", "-png", "-gray", "-r", str(dpi), "-f", str(page_no),
                    "-l", str(page_no), pdf, "/tmp/_full"], check=True, capture_output=True)
    f = sorted(glob.glob("/tmp/_full*.png"))[-1]
    im = Image.open(f)
    arr = np.array(im.convert("L"))
    os.remove(f)
    _CACHE.clear()
    _CACHE[key] = arr
    return arr


def _blank_rows(arr, y0, y1, x0, x1, thr=250):
    sub = arr[max(0, y0):y1, x0:x1]
    return (sub >= thr).mean(axis=1) > 0.995


def _blank_cols(arr, y0, y1, x0, x1, thr=250):
    sub = arr[y0:y1, max(0, x0):x1]
    return (sub >= thr).mean(axis=0) > 0.995


def expand_box(arr, box_px, max_grow=70, run=6):
    """box_px = (x0, y0, x1, y1) in image pixels."""
    h, w = arr.shape
    x0, y0, x1, y1 = [int(v) for v in box_px]
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(w, x1); y1 = min(h, y1)
    # up
    for step in range(1, max_grow):
        yy = y0 - step
        if yy < 1:
            break
        if _blank_rows(arr, yy - run, yy, x0, x1).all():
            y0 = yy; break
    # down
    for step in range(1, max_grow):
        yy = y1 + step
        if yy >= h - 1:
            break
        if _blank_rows(arr, yy, yy + run, x0, x1).all():
            y1 = yy; break
    # left
    for step in range(1, max_grow):
        xx = x0 - step
        if xx < 1:
            break
        if _blank_cols(arr, y0, y1, xx - run, xx).all():
            x0 = xx; break
    # right
    for step in range(1, max_grow):
        xx = x1 + step
        if xx >= w - 1:
            break
        if _blank_cols(arr, y0, y1, xx, xx + run).all():
            x1 = xx; break
    return x0, y0, x1, y1


def snap_to_lines(arr, box, win=110, frac=0.7):
    """Snap box edges to nearby long straight lines (bordered boxes, chart frames)."""
    h, w = arr.shape
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(w, x1); y1 = min(h, y1)
    def dark_col(x, ya, yb):
        if x < 0 or x >= w:
            return False
        seg = arr[ya:yb, x]
        return (seg < 236).mean() >= frac
    def dark_row(y, xa, xb):
        if y < 0 or y >= h:
            return False
        seg = arr[y, xa:xb]
        return (seg < 236).mean() >= frac
    for d in range(win, 2, -1):
        if dark_col(x0 - d, y0, y1):
            x0 -= d - 1; break
    for d in range(win, 2, -1):
        if dark_col(x1 + d - 1, y0, y1):
            x1 += d; break
    for d in range(win, 2, -1):
        if dark_row(y0 - d, x0, x1):
            y0 -= d - 1; break
    for d in range(win, 2, -1):
        if dark_row(y1 + d - 1, x0, x1):
            y1 += d; break
    return x0, y0, x1, y1


def crop_figure(pdf, page_no, box, out_png, dpi=190, grow=True, pad=3):
    """box in xml coordinates (812x1131 page space)."""
    sc = dpi / 72.0
    arr = page_image(pdf, page_no, 150)
    h, w = arr.shape
    # xml space -> 150dpi pixel space
    kx, ky = w / 812.0, h / 1131.0
    px = [box[0] * kx, box[1] * ky, box[2] * kx, box[3] * ky]
    if grow:
        px = snap_to_lines(arr, px)
        px = expand_box(arr, px)
    px = [px[0] - pad, px[1] - pad, px[2] + pad, px[3] + pad]
    # back to xml space
    bx = [px[0] / kx, px[1] / ky, px[2] / kx, px[3] / ky]
    sc2 = dpi / 72.0
    import re as _re
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    mm = _re.search(r"Page size:\s+([\d.]+) x", info)
    k = (float(mm.group(1)) / 812.0) if mm else (595.0 / 812.0)
    p = [v * k * sc2 for v in bx]
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no),
                    "-x", str(int(p[0])), "-y", str(int(p[1])),
                    "-W", str(max(1, int(p[2] - p[0]))), "-H", str(max(1, int(p[3] - p[1]))),
                    pdf, "/tmp/_c"], check=True, capture_output=True)
    files = sorted(glob.glob("/tmp/_c*.png"))
    if not files:
        return False
    Image.open(files[0]).convert("RGB").save(out_png)
    for f in files:
        os.remove(f)
    return True
