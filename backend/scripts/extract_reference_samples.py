"""从真实投标文件抽取参考样本，按二级章节切分输出 jsonl

输入：1 docx + 2 pdf（合肥新安彩印真实投标）
输出：data/reference_samples.jsonl，每行 {source, title, content, length}

执行：cd backend && python3 scripts/extract_reference_samples.py
"""

import json
import os
import re
import sys

import fitz
from docx import Document

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "reference_samples.jsonl")

# 三份源文件
DOCX_FILE = "/Users/wangyunchen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wangyunchen002_9c8a/msg/file/2026-05/1871响应文件格式.docx"
PDF_FILES = [
    "/Users/wangyunchen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wangyunchen002_9c8a/msg/file/2026-05/合肥新安彩印包装有限公司投标文件(1).pdf",
    "/Users/wangyunchen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wangyunchen002_9c8a/msg/file/2026-05/合肥新安彩印包装有限公司投标文件.pdf",
]

# 二级章节标题正则：（一）/ 一、 / 第X节 / X.1
HEADER_RE = re.compile(
    r'^(?:[（(][一二三四五六七八九十]+[）)]|[一二三四五六七八九十]+、|第[一二三四五六七八九十]+(?:章|节)|[\d]+\.[\d]+\s)\s*[^.\n]{2,40}$'
)


def is_chapter_heading(text: str) -> bool:
    text = text.strip()
    if not text or len(text) > 80:
        return False
    # 跳过目录行（含点连接符 ........ 和页码）
    if re.search(r'\.{4,}\s*\d+\s*$', text):
        return False
    return bool(HEADER_RE.match(text))


def chunk_by_heading(lines: list[str]) -> list[dict]:
    """按章节标题切分，返回 [{title, content}]"""
    chunks = []
    cur_title = None
    cur_buf: list[str] = []

    def flush():
        if cur_title and cur_buf:
            content = "\n".join(s for s in cur_buf if s.strip())
            content = re.sub(r'\n{3,}', '\n\n', content).strip()
            if len(content) > 100:  # 太短的丢掉
                chunks.append({"title": cur_title, "content": content})

    for line in lines:
        line = line.rstrip()
        if is_chapter_heading(line):
            flush()
            cur_title = line.strip()
            cur_buf = []
        else:
            cur_buf.append(line)
    flush()
    return chunks


def extract_docx(path: str) -> list[dict]:
    doc = Document(path)
    lines = [p.text for p in doc.paragraphs]
    return chunk_by_heading(lines)


def extract_pdf(path: str) -> list[dict]:
    doc = fitz.open(path)
    lines = []
    for page in doc:
        lines.extend(page.get_text("text").split("\n"))
    doc.close()
    return chunk_by_heading(lines)


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    all_samples = []

    for fp in [DOCX_FILE]:
        if not os.path.exists(fp):
            print(f"⚠️ 文件不存在: {fp}")
            continue
        chunks = extract_docx(fp)
        source = os.path.basename(fp)
        print(f"\n[docx] {source}: {len(chunks)} 个章节")
        for c in chunks:
            c["source"] = source
            c["length"] = len(c["content"])
            all_samples.append(c)

    for fp in PDF_FILES:
        if not os.path.exists(fp):
            print(f"⚠️ 文件不存在: {fp}")
            continue
        chunks = extract_pdf(fp)
        source = os.path.basename(fp)
        print(f"\n[pdf]  {source}: {len(chunks)} 个章节")
        for c in chunks:
            c["source"] = source
            c["length"] = len(c["content"])
            all_samples.append(c)

    # 按字数过滤：300-8000 字才有价值（太短没料、太长是杂烩）
    filtered = [s for s in all_samples if 300 <= s["length"] <= 8000]
    print(f"\n总章节 {len(all_samples)} 个，过滤后 {len(filtered)} 个（300-8000 字）")

    # 字数分布
    buckets = {"300-500": 0, "500-1000": 0, "1000-2000": 0, "2000-4000": 0, "4000-8000": 0}
    for s in filtered:
        n = s["length"]
        if n < 500: buckets["300-500"] += 1
        elif n < 1000: buckets["500-1000"] += 1
        elif n < 2000: buckets["1000-2000"] += 1
        elif n < 4000: buckets["2000-4000"] += 1
        else: buckets["4000-8000"] += 1
    print("字数分布:", buckets)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for s in filtered:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\n✓ 已写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
