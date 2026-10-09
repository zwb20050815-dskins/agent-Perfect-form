"""把笔记目录里的 HTML 与 PDF 文字放入同一个知识库。"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import httpx
from langchain_openai import OpenAIEmbeddings

from lesson02 import convert_html
from lesson03a import split_markdown
from lesson03b import PROJECT_DIR, LessonError, load_chunks, read_config
from lesson06b import report_error

LIBRARY_NAME = "个人笔记"
LIBRARY_SOURCE = PROJECT_DIR / f"data/chunks/{LIBRARY_NAME}.chunks.json"
LIBRARY_INDEX = PROJECT_DIR / f"data/vectors/{LIBRARY_NAME}.vectors.json"
REPORT_PATH = PROJECT_DIR / "data/library/import-report.json"
DEFAULT_NOTES = Path(r"C:\Users\Zwb\Desktop\笔记")


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def split_text(text, size=600, overlap=80):
    """优先在换行或句末断开；较长文字保留少量重叠，且不会跨PDF页。"""
    if not 0 <= overlap < size // 2:
        raise ValueError("overlap 必须小于目标长度的一半。")
    text, start = text.strip(), 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind(mark, start + size // 2, end) for mark in ("\n", "。", "；", "; ", ". "))
            if cut >= 0:
                end = cut + 1
        part = text[start:end].strip()
        if part:
            yield part
        if end == len(text):
            break
        start = end - overlap


def clean_pdf_text(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # OneNote的打印页脚不作为知识，保留正文与实际页码的对应关系。
    text = re.sub(r"(?m)^[ \t]*分区[^\n]*的第\s*\d+\s*页[ \t]*$", "", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", "\n".join(lines)).strip()


def pdf_chunks(source, doc_id, output, chunk_size):
    from pypdf import PdfReader

    reader = PdfReader(source)
    if reader.is_encrypted and not reader.decrypt(""):
        raise LessonError(f"{source.name} 需要密码，本轮未更新知识块文件。")
    chunks, pages, markdown = [], [], [f"# {source.stem}\n\n> 来源：{source.name}"]
    for number, page in enumerate(reader.pages, 1):
        text = clean_pdf_text(page.extract_text(extraction_mode="layout") or "")
        image_count = len(page.images)
        nonspace = len(re.sub(r"\s", "", text))
        if "\ufffd" in text:
            raise LessonError(f"{source.name} 第{number}页存在无法解码的文字，请先检查提取结果。")
        pages.append({"page": number, "text_characters": nonspace, "images": image_count,
                      "low_text": nonspace < 50, "needs_ocr_review": image_count > 0})
        markdown.append(f"## PDF物理第 {number} 页\n\n" + (text or "（未提取到文字，需要人工检查或OCR）"))
        for part in split_text(text, chunk_size):
            chunks.append({"chunk_id": f"{doc_id}:{len(chunks) + 1:04d}",
                           "source_file": source.name, "source_path": str(source.resolve()),
                           "heading_path": [source.stem, f"PDF物理第 {number} 页"],
                           "page": number, "text": part, "char_count": len(part)})
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{doc_id}.md").write_text("\n\n".join(markdown) + "\n", encoding="utf-8")
    metadata = {"source_file": source.name, "source_path": str(source.resolve()),
                "format": "pdf", "pages": pages, "chunks": len(chunks),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    save_json(output / f"{doc_id}.json", metadata)
    return chunks, metadata


def html_chunks(source, doc_id, output, chunk_size):
    # 使用每篇文档自己的目录，避免同名HTML/PDF覆盖中间文件。
    markdown_path, _, metadata = convert_html(source, output / doc_id)
    chunks = split_markdown(markdown_path.read_text(encoding="utf-8"), metadata, doc_id, chunk_size)
    bounded = []
    for chunk in chunks:
        # 原课程保留整张表；很长的表在扩充库中分段，保留章节标题供检索。
        parts = split_text(chunk["text"], chunk_size) if len(chunk["text"]) > 1200 else [chunk["text"]]
        for text in parts:
            bounded.append({**chunk, "chunk_id": f"{doc_id}:{len(bounded) + 1:04d}",
                            "text": text, "char_count": len(text)})
    return bounded, {"source_file": source.name, "format": "html", "chunks": len(bounded),
                     "source_sha256": metadata["source_sha256"], "images": metadata["image_count"]}


def prepare_library(notes_dir, chunk_size=600):
    notes_dir = notes_dir.resolve()
    if not notes_dir.is_dir():
        raise LessonError("笔记目录不存在，请检查 --notes-dir。")
    files = sorted(path for path in notes_dir.rglob("*") if path.is_file()
                   and path.suffix.lower() in (".html", ".htm", ".pdf"))
    if not files:
        raise LessonError("目录中没有 HTML 或 PDF。")
    names = Counter(path.stem.casefold() for path in files)
    chunks, documents = [], []
    output = PROJECT_DIR / "data/library/markdown"
    for source in files:
        relative = source.relative_to(notes_dir).as_posix()
        # 旧会计笔记保留原ID；同名文件加相对路径摘要，避免RRF把不同资料合并。
        doc_id = re.sub(r"[^\w.-]", "_", source.stem)
        if names[source.stem.casefold()] > 1 or doc_id != source.stem:
            doc_id += "-" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
        print(f"[prepare] {relative}", flush=True)
        if source.suffix.lower() == ".pdf":
            rows, metadata = pdf_chunks(source, doc_id, output, chunk_size)
        else:
            rows, metadata = html_chunks(source, doc_id, output, chunk_size)
        metadata["relative_path"] = relative
        documents.append(metadata)
        chunks.extend(rows)
    if not chunks or len({row["chunk_id"] for row in chunks}) != len(chunks):
        raise LessonError("没有可检索的文字或资料编号冲突，本轮未更新知识块。")
    report = {"notes_dir": str(notes_dir), "documents": documents, "total_chunks": len(chunks),
              "pdf_pages": sum(len(doc.get("pages", [])) for doc in documents),
              "pdf_image_pages": sum(page["needs_ocr_review"] for doc in documents for page in doc.get("pages", [])),
              "pdf_low_text_pages": sum(page["low_text"] for doc in documents for page in doc.get("pages", [])),
              "limitation": "仅导入文字层；PDF截图与HTML图片中的文字尚未OCR。物理页码从1开始。"}
    save_json(REPORT_PATH, report)
    save_json(LIBRARY_SOURCE, chunks)
    print(f"已提取 {len(documents)} 份文件，生成 {len(chunks)} 个知识块。", flush=True)
    print(f"PDF共 {report['pdf_pages']} 页；其中 {report['pdf_image_pages']} 页含图，"
          f"{report['pdf_low_text_pages']} 页提取文字少于50字。图片内容尚未OCR。", flush=True)
    print(f"覆盖情况：{REPORT_PATH}", flush=True)
    return chunks


def index_library(chunks):
    from library_index import build_library_index

    config = read_config()
    seeds = [path for path in (PROJECT_DIR / "data/vectors").glob("*.vectors.json") if path != LIBRARY_INDEX]
    with httpx.Client(follow_redirects=False) as client:
        model = OpenAIEmbeddings(**config, check_embedding_ctx_length=False, chunk_size=10,
            model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client)
        stats = build_library_index(chunks, config, model, LIBRARY_INDEX, seed_paths=seeds)
    print(f"统一索引可用：{stats['total']} 块；复用 {stats['reused']} 块，本次新生成 {stats['embedded']} 个向量。")
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "index", "build"), nargs="?", default="build")
    parser.add_argument("--notes-dir", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--chunk-size", type=int, default=600)
    args = parser.parse_args()
    if not 200 <= args.chunk_size <= 1200:
        parser.error("本项目块长度请使用200～1200字符。")
    try:
        chunks = (prepare_library(args.notes_dir, args.chunk_size) if args.action in ("prepare", "build")
                  else load_chunks(LIBRARY_SOURCE))
        if args.action != "prepare":
            index_library(chunks)
        return 0
    except ModuleNotFoundError:
        print("缺少依赖，请先运行 uv sync。")
    except Exception as exc:
        report_error(exc)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
