"""命令行入口：配置一份 config.json，一条命令跑完 解析 → 定页码 → 裁图 → Word/PPT。"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wbook import parse_pdf, parse_md, paginate, model, build_docx, build_pptx


def load_config(path):
    cfg = json.load(open(path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(path))
    out = cfg.get("out", "out")
    cfg["out"] = out if os.path.isabs(out) else os.path.join(base, out)
    os.makedirs(cfg["out"], exist_ok=True)
    brand = cfg.get("brand")
    if brand and brand.get("qrcode") and not os.path.isabs(brand["qrcode"]):
        brand["qrcode"] = os.path.join(base, brand["qrcode"])
    for b in cfg["books"]:
        for k in ("pdf", "md", "answers_md"):
            if b.get(k) and not os.path.isabs(b[k]):
                b[k] = os.path.join(base, b[k])
    return cfg


def one_book(cfg, b):
    tag = str(b["tag"])
    out = cfg["out"]
    if b["source"] == "pdf":
        chapters = parse_pdf.run(b["pdf"], b.get("page_offset", 4))
        book_json = os.path.join(out, f"book{tag}.json")
        json.dump(chapters, open(book_json, "w"), ensure_ascii=False, indent=1)
    else:
        chapters = parse_md.run(b["md"], b.get("chapters", []), b.get("exams", []), b.get("pdf"))
        book_json = os.path.join(out, f"book{tag}_raw.json")
        json.dump(chapters, open(book_json, "w"), ensure_ascii=False, indent=1)
        paged = os.path.join(out, f"book{tag}.json")
        paginate.run(b["pdf"], book_json, paged, b.get("page_offset", 4))
    return book_json


def main():
    ap = argparse.ArgumentParser(prog="wbook", description="教辅 → Word + 投屏 PPT")
    ap.add_argument("--config", required=True, help="config.json 路径")
    ap.add_argument("--step", default="all", choices=["parse", "model", "docx", "pptx", "all"])
    args = ap.parse_args()

    cfg = load_config(args.config)
    books = cfg["books"]
    out = cfg["out"]

    if args.step in ("parse", "all"):
        for b in books:
            one_book(cfg, b)
            print(f"[parse] {b['tag']} -> {out}")

    ans = {str(b["tag"]): b.get("answers_md") for b in books}
    pdfs = {str(b["tag"]): b["pdf"] for b in books}

    if args.step in ("model", "all"):
        model.run(out, pdfs, ans)
        print("[model] 裁图 + 答案 ok")

    for b in books:
        tag = str(b["tag"])
        model_path = os.path.join(out, f"model{tag}.json")
        if args.step in ("docx", "all"):
            p = build_docx.run(model_path, os.path.join(out, f"{b['title']}.docx"),
                               b["title"], b.get("subtitle", "试题与答案"), b.get("note", ""),
                               cfg.get("brand"))
            print("[docx]", p)
        if args.step in ("pptx", "all"):
            p = build_pptx.run(model_path, os.path.join(out, f"{b['title']}_讲评.pptx"),
                               b["title"], b.get("subtitle_ppt", "试题讲评 · 一题一页"),
                               b.get("note", ""), os.path.join(out, "pptimg"), cfg.get("brand"))
            print("[pptx]", p)


if __name__ == "__main__":
    main()
