# workbook-to-docx-pptx

简体中文 ｜ [English](#english)

把中文教辅（习题册、目标检测、单元卷）转成两份可直接用的成品：

- **Word**：按章 / 节排版的试题册，保留插图、表格、填空下划线，每题右侧标原书页码，**每节末集中给参考答案**。
- **PPT**：16:9 投屏讲评版，**一题一页 + 紧接一页答案**，每节先来一页知识网络，右上角「原书 P0XX · 第 N 题」。

为初中物理 / 地理《学习目标与检测》这类书写的，也适用于绝大多数国内教辅排版。

## 为什么不用逐页 OCR

一页一页看图转写，96 页要两三个小时，而且每次重排都要重来一遍。这个工具走两条更快的路：

| 输入 | 做法 | 一册 80–100 页耗时 |
|---|---|---|
| MinerU 等工具导出的 **markdown** | 文字全从 md 来，PDF 只用来**裁图 + 定页码** | 约 2 分钟 |
| **有文本层的 PDF** | `pdftohtml -xml` 抽行和坐标，零 OCR | 约 2 分钟 |
| 纯图片 PDF | 才退回逐页转写（1–2 分钟/页） | 2–3 小时 |

## 安装

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install python-docx python-pptx pillow
# 需要 poppler 提供 pdftohtml / pdftoppm / pdfinfo
#   macOS: brew install poppler
#   Ubuntu: apt install poppler-utils
# 需要 LibreOffice 做 QA 转 PDF（可选）
```

## 用法

```bash
# 1. 复制示例配置，改成自己的路径
cp examples/config.json my.json

# 2. 一条命令跑完：解析 → 定页码 → 裁图 → Word/PPT
python3 -m wbook.cli --config my.json

# 也可以分步
python3 -m wbook.cli --config my.json --step parse
python3 -m wbook.cli --config my.json --step model
python3 -m wbook.cli --config my.json --step docx
python3 -m wbook.cli --config my.json --step pptx
```

产出在配置里的 `out/`：`<书名>.docx`、`<书名>_讲评.pptx`。

## 配置

```json
{
  "out": "out",
  "books": [
    {
      "tag": "7",
      "source": "pdf",
      "pdf": "书.pdf",
      "page_offset": 4,
      "answers_md": "答案.md",
      "title": "学习目标与检测·七年级地理（上）",
      "subtitle": "试题与答案",
      "note": "共 5 章 16 节"
    },
    {
      "tag": "8",
      "source": "md",
      "pdf": "书.pdf",
      "md": "MinerU.md",
      "page_offset": 4,
      "answers_md": "答案.md",
      "title": "学习目标与检测·八年级地理（上）",
      "chapters": [["第一章 …", [["第一节 …", 1], ["第二节 …", 5]]]],
      "exams": [["综合练习一", 61]]
    }
  ]
}
```

- `source`：`pdf` 表示 PDF 有文本层；`md` 表示用 MinerU 的 markdown。
- `page_offset`：**印刷页码 = PDF 页码 − 这个数**（前附件页数）。
- `chapters` / `exams`：目录里的节名和起始页。PDF 有文本层时不用写（会自己识别标题），只有 md 来源才需要。

## 版式规则（这些是硬要求）

- `（　　）` 用不换行空格填充，**绝不允许断成两行**。
- **A/B/C/D 选项必须另起一行，A 顶行首**，按字数 4 / 2 / 1 个一行；①②③④ 同理。
- 试题前的**材料段用楷体**，题干用宋体（Word）/ 微软雅黑（PPT）。
- 双栏「观察—思考」卡片、带表格的资料卡：**整块裁图当插图**，不要把文字拉平。
- 答案页：题干 19–24pt 复述，答案 34pt 起，分区线跟着题干高度走。

## 已知限制

- **没有文本层的册子**（文字被转曲、`pdffonts` 为空）只能靠目录页号 + 灰底标签条锚定页码，再按行数估算节内分布，个别题可能差一页；图也按顺序对应，个别会错位。
- 两栏排布的选项组（A、C 一行 / B、D 一行）偶尔仍会把相邻条目吸进选项，需要对着原书扫一眼。
- 中文 OCR 没做，也不打算做——请先用 MinerU 之类的工具把 PDF 转成 markdown。

## 目录结构

```
wbook/
  cli.py          命令行入口
  parse_pdf.py    有文本层的 PDF → 结构（pdftohtml）
  parse_md.py     MinerU markdown → 结构
  paginate.py     md 来源：锚点 + 行数估算定页码
  answers.py      答案册 → 每节答案
  model.py        裁图、并答案、文本清理（LaTeX 碎片、折行合并、材料/题干切分）
  build_docx.py   Word
  build_pptx.py   投屏 PPT
  pdfxml.py       坐标换算与裁图
  cropfig.py      贴边吸附 + 外扩裁图
  vecfig.py       矢量图形块探测
  columns.py      双栏卡片分栏重排
  layout.py       题干拆条、每行几个、行高估算
```

## 关于公众号「智教云栈」

> 关注 「智教云栈」，一线教师 + AI 教育工具，不吹「一键」，只讲「怎么改」。
>
> 🔧 智教云栈 ｜ 智学题库 ｜ 云栈课堂

备课之余，遇到试卷下载、题目找寻、组卷，或视频剪辑、格式转换、课件排版等小烦恼，不必独自费心。公众号留言，愿以绵薄之力，伴您从容前行。

<p align="center">
  <img src="images/qrcode.png" width="220" alt="智教云栈 公众号二维码">
</p>

这个工具就是备课时攒出来的：两册《学习目标与检测》一百六十多页，一题一页地对下来，顺手把流程写成了代码。用法上有问题、或者想改成你们学校自己的版式，公众号后台留言就行。

## 版权

代码 MIT。**教材内容（PDF、markdown、裁出来的图、生成的 docx/pptx）版权归原出版方，不要提交到本仓库，也不要分发。**

---

## English

**Turn a Chinese workbook into an editable Word file and a 16:9 review deck.**

Built for the *学习目标与检测* series (Chinese middle-school geography / physics workbooks), and general enough for most workbook layouts: chapters and sections, multiple-choice questions with A–D options, fill-in-the-blank items, numbered sub-questions, figures and tables, plus a separate answer key.

**What you get**

- **Word** — A4, chapter/section layout, figures and tables preserved, a small page tag (`原书 P012`) beside every question, answers collected at the end of each section.
- **PPT** — 16:9, one question per slide followed by its answer slide, a knowledge-map slide at the start of each section, header showing the original page and question number.

**Why not OCR**

Transcribing a book page by page takes hours and has to be redone after every layout change. This tool takes a faster route:

| Input | Approach | Time for an 80–100 page book |
|---|---|---|
| **MinerU markdown export** | text comes from the markdown; the PDF is only used to crop figures and locate pages | ~2 min |
| **PDF with a text layer** | `pdftohtml -xml` yields lines and coordinates, no OCR | ~2 min |
| Image-only PDF | falls back to page-by-page transcription | 2–3 h |

**Requirements**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install python-docx python-pptx pillow
# poppler-utils provides pdftohtml / pdftoppm / pdfinfo
```

**Usage**

```bash
cp examples/config.json my.json      # edit paths, page offset, table of contents
python3 -m wbook.cli --config my.json
```

Outputs land in `out/`: `<book>.docx` and `<book>_review.pptx`.

**Layout rules it enforces**

- Answer brackets `（　　）` never break across lines.
- A/B/C/D options always start a new line with `A` at the margin — four per row when very short, two when medium, one otherwise; ①②③④ items follow the same rule.
- Source material above a question is set in KaiTi; question text in SimSun (Word) or Microsoft YaHei (PPT).
- Two-column "observe / think" cards are cropped as a single image instead of being linearised.
- LaTeX leftovers from the markdown (`$30^{\circ}\mathrm{N}$`) are normalised to `30°N`, `20℃`, `4~5`.

**Known limitations**

- For image-only PDFs, page numbers are estimated from the table of contents and the grey section labels, so a few may be off by one page.
- Two-column option blocks can occasionally pull a neighbouring item into an option.
- No Chinese OCR — run MinerU (or similar) first.

**License**

Code is MIT. Book content (PDFs, markdown, cropped figures, generated documents) remains the copyright of its publisher — please do not commit or redistribute it.

**Contact**

Questions, bug reports, or a layout you would like supported: **support@aiquickspot.com**

