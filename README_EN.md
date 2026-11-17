# workbook-to-docx-pptx

[简体中文](README.md) ｜ English

**Turn a Chinese workbook into an editable Word file and a 16:9 review deck.**

Built for the *学习目标与检测* series (Chinese middle-school geography / physics workbooks), and general enough for most workbook layouts: chapters and sections, multiple-choice questions with A–D options, fill-in-the-blank items, numbered sub-questions, figures and tables, plus a separate answer key.

## What you get

- **Word** — A4, chapter/section layout, figures and tables preserved, a small page tag (`原书 P012`) beside every question, answers collected at the end of each section.
- **PPT** — 16:9, one question per slide followed by its answer slide, a knowledge-map slide at the start of each section, header showing the original page and question number.

## Why not OCR

Transcribing a book page by page takes hours and has to be redone after every layout change. This tool takes a faster route:

| Input | Approach | Time for an 80–100 page book |
|---|---|---|
| **MinerU markdown export** | text comes from the markdown; the PDF is only used to crop figures and locate pages | ~2 min |
| **PDF with a text layer** | `pdftohtml -xml` yields lines and coordinates, no OCR | ~2 min |
| Image-only PDF | falls back to page-by-page transcription | 2–3 h |

## Requirements

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install python-docx python-pptx pillow
# poppler-utils provides pdftohtml / pdftoppm / pdfinfo
#   macOS: brew install poppler
#   Ubuntu: apt install poppler-utils
# LibreOffice is optional (QA: convert to PDF)
```

## Usage

```bash
cp examples/config.json my.json      # edit paths, page offset, table of contents
python3 -m wbook.cli --config my.json

# Or step by step
python3 -m wbook.cli --config my.json --step parse
python3 -m wbook.cli --config my.json --step model
python3 -m wbook.cli --config my.json --step docx
python3 -m wbook.cli --config my.json --step pptx
```

Outputs land in `out/`: `<book>.docx` and `<book>_review.pptx`.

## Configuration

```json
{
  "out": "out",
  "books": [
    {
      "tag": "7",
      "source": "pdf",
      "pdf": "book.pdf",
      "page_offset": 4,
      "answers_md": "answers.md",
      "title": "Learning Goals & Checks · Grade 7 Geography",
      "subtitle": "Questions and answers",
      "note": "5 chapters, 16 sections"
    },
    {
      "tag": "8",
      "source": "md",
      "pdf": "book.pdf",
      "md": "MinerU.md",
      "page_offset": 4,
      "answers_md": "answers.md",
      "title": "Learning Goals & Checks · Grade 8 Geography",
      "chapters": [["Chapter 1 …", [["Section 1 …", 1], ["Section 2 …", 5]]]],
      "exams": [["Practice Exam 1", 61]]
    }
  ]
}
```

- `source`: `pdf` = PDF has a text layer; `md` = use MinerU markdown.
- `page_offset`: **print page = PDF page − this value** (front-matter pages).
- `chapters` / `exams`: section titles and start pages from the table of contents. Not needed for text-layer PDFs (titles are detected); required for markdown input.

## Layout rules it enforces

- Answer brackets `（　　）` never break across lines.
- A/B/C/D options always start a new line with `A` at the margin — four per row when very short, two when medium, one otherwise; ①②③④ items follow the same rule.
- Source material above a question is set in KaiTi; question text in SimSun (Word) or Microsoft YaHei (PPT).
- Two-column "observe / think" cards are cropped as a single image instead of being linearised.
- LaTeX leftovers from the markdown (`$30^{\circ}\mathrm{N}$`) are normalised to `30°N`, `20℃`, `4~5`.

## Known limitations

- For image-only PDFs, page numbers are estimated from the table of contents and the grey section labels, so a few may be off by one page.
- Two-column option blocks can occasionally pull a neighbouring item into an option.
- No Chinese OCR — run MinerU (or similar) first.

## Project layout

```
wbook/
  cli.py          CLI entry
  parse_pdf.py    text-layer PDF → structure (pdftohtml)
  parse_md.py     MinerU markdown → structure
  paginate.py     md source: anchors + line estimates for page numbers
  answers.py      answer booklet → per-section answers
  model.py        crop figures, merge answers, clean text
  build_docx.py   Word
  build_pptx.py   review PPT
  pdfxml.py       coordinate mapping and cropping
  cropfig.py      snap-to-edge + expand crop
  vecfig.py       vector figure block detection
  columns.py      two-column card reflow
  layout.py       stem splitting, columns-per-row, line-height estimates
```

## About AIQuickSpot

This project is part of **[AIQuickSpot](https://www.aiquickspot.com)** — practical AI tools for everyday teaching and content work.

Questions, bug reports, or a layout you would like supported: **support@aiquickspot.com**

## License

Code is MIT. Book content (PDFs, markdown, cropped figures, generated documents) remains the copyright of its publisher — please do not commit or redistribute it.
