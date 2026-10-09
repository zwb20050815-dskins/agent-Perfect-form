"""第三课 3.1：按标题和段落切块，为每一块保留来源。"""

import argparse
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = PROJECT_DIR / "data" / "markdown" / "银行会计重点笔记.md"
DEFAULT_OUTPUT = PROJECT_DIR / "data" / "chunks"


def split_markdown(markdown: str, source: dict, document_name: str,
                   chunk_size: int = 600) -> list[dict]:
    """处理第二课生成的 Markdown；按完整段落和表格组块。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0。")
    # 第二课加上的来源说明已在 JSON 中记录，无需重复当作知识正文。
    prefix = f"> 来源：{source['source_file']}"
    if markdown.startswith(prefix + "\n"):
        markdown = markdown[len(prefix):].lstrip("\n")

    chunks = []
    headings = []  # 保存 (标题级别, 标题文字)。
    paragraphs = []
    heading_has_chunk = False

    def save_chunk() -> None:
        nonlocal heading_has_chunk
        if not paragraphs:
            return
        text = "\n\n".join(paragraphs)
        chunks.append({
            "chunk_id": f"{document_name}:{len(chunks) + 1:04d}",
            "source_file": source["source_file"],
            "source_path": source["source_path"],
            "heading_path": [title for level, title in headings] or [source["title"]],
            "text": text,
            "char_count": len(text),
        })
        paragraphs.clear()
        heading_has_chunk = True

    # 本课输入用空行分隔标题、段落和表格；一整张表保持在同一个块里。
    for paragraph in re.split(r"\n\s*\n", markdown.strip()):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        heading = re.fullmatch(r"(#{1,6})[ \t]+(.+)", paragraph)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            save_chunk()
            # 标题也可能包含知识：被同级/上级标题替换前，保留尚无正文的标题。
            if headings and not heading_has_chunk and level <= headings[-1][0]:
                paragraphs.append(headings[-1][1])
                save_chunk()
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            heading_has_chunk = False
            continue

        # 加上下一段会超过目标长度时，先保存已有段落，再开一个新块。
        candidate = "\n\n".join(paragraphs + [paragraph])
        if paragraphs and len(candidate) > chunk_size:
            save_chunk()
        paragraphs.append(paragraph)
    if headings and not paragraphs and not heading_has_chunk:
        paragraphs.append(headings[-1][1])
    save_chunk()
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="输入 Markdown 文件")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="结果保存目录")
    parser.add_argument("--chunk-size", type=int, default=600, help="目标块长度，按字符计算")
    args = parser.parse_args()
    if args.chunk_size <= 0:
        parser.error("--chunk-size 必须大于 0。")
    if args.source.suffix.lower() != ".md":
        parser.error("--source 应指向第二课生成的 .md 文件。")
    try:
        markdown = args.source.read_text(encoding="utf-8-sig")
        source = json.loads(args.source.with_suffix(".json").read_text(encoding="utf-8-sig"))
        chunks = split_markdown(markdown, source, args.source.stem, args.chunk_size)
        if not chunks:
            raise ValueError("没有找到可切块的正文。")
        args.output.mkdir(parents=True, exist_ok=True)
        output_file = args.output / f"{args.source.stem}.chunks.json"
        output_file.write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"切块失败：{exc}；请确认第二课的 .md 和同名 .json 文件都存在且完整。\n")
    print(f"已生成 {len(chunks)} 个知识块：{output_file.resolve()}")
    print(f"目标长度：{args.chunk_size} 字符；实际块长度："
          f"{min(c['char_count'] for c in chunks)}–{max(c['char_count'] for c in chunks)} 字符。")
    oversized = sum(c["char_count"] > args.chunk_size for c in chunks)
    if oversized:
        print(f"其中 {oversized} 块超过目标长度：为了保持完整，未拆开长段落或表格。")
    print("首块标题：" + " > ".join(chunks[0]["heading_path"]))
    print("首块预览：" + chunks[0]["text"][:100].replace("\n", " "))


if __name__ == "__main__":
    main()
