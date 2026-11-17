"""Detect vector figure regions on a page render (八年级 pages draw many figures as paths)."""
import subprocess, glob, os
import numpy as np
from PIL import Image


def render(pdf, page_no, dpi=110, tag="v"):
    subprocess.run(["pdftoppm", "-png", "-gray", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no),
                    pdf, f"/tmp/_{tag}"], check=True, capture_output=True)
    f = sorted(glob.glob(f"/tmp/_{tag}*.png"))[-1]
    im = Image.open(f)
    arr = np.array(im.convert("L"))
    os.remove(f)
    return arr


def bands_from(arr, x0, x1, thr_frac=0.008):
    sub = arr[:, x0:x1]
    ink = (sub < 170).sum(axis=1)
    thr = max(2, int((x1 - x0) * thr_frac))
    rows = ink > thr
    out, start = [], None
    for i, v in enumerate(rows):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 3:
                out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(rows)))
    return out


def graphics_boxes(arr, W_xml=812.0, H_xml=1131.0, dpi=110):
    """Return candidate figure boxes in xml coordinates."""
    h, w = arr.shape
    sx, sy = W_xml / w, H_xml / h
    x0, x1 = int(w * 0.10), int(w * 0.93)
    bands = bands_from(arr, x0, x1)
    # classify: text line = short band (< 0.032*h) ; graphic = tall band or irregular gap
    fig_bands = []
    for (a, b) in bands:
        bh = (b - a) * sy
        if bh > 34:
            fig_bands.append((a, b))
    # group nearby figure bands
    groups = []
    for a, b in fig_bands:
        if groups and a - groups[-1][1] < 5:
            groups[-1] = (groups[-1][0], b)
        else:
            groups.append((a, b))
    boxes = []
    for a, b in groups:
        if (b - a) * sy < 40:
            continue
        # horizontal extent of ink in this band
        sub = arr[a:b, x0:x1]
        col = (sub < 170).sum(axis=0)
        nz = np.nonzero(col > max(2, 0.01 * (b - a)))[0]
        if len(nz) == 0:
            continue
        left = x0 + nz[0]; right = x0 + nz[-1]
        boxes.append([left * sx, a * sy, right * sx, b * sy])
    return boxes
