"""第二课：把一份 HTML 笔记转成 Markdown，并记录来源。"""

import argparse
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify

DEFAULT_SOURCE = Path(r"C:\Users\Zwb\Desktop\笔记\银行会计重点笔记.html")
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "markdown"


def convert_html(source: Path, output_dir: Path) -> tuple[Path, Path, dict]:
    # 1. 读取原文件；HTMLParser 只解析标签，不执行网页脚本。
    raw = source.read_bytes()
    soup = BeautifulSoup(raw, "html.parser", from_encoding="utf-8")
    body = soup.body
    if body is None:
        raise ValueError("文件没有 body 标签，本课脚本需要完整的 HTML 页面。")

    # 2. 去掉网页装饰与重复目录，保留知识正文。
    for tag in body.select("script, style, nav, footer, .badge, .legend"):
        tag.decompose()
    for tag in body.select("span.key, span.tag-red, span.tag-blue, span.tag-green"):
        tag.name = "strong"  # 原来的彩色重点转成 Markdown 加粗。

    # 把表格标题移到表格前面，让 Markdown 保留完整的表格结构。
    for caption in body.select("table > caption"):
        table = caption.parent
        caption.extract()
        caption.name = "p"
        table.insert_before(caption)

    # 3. 记录文件与章节来源，后面的 RAG 会用到这些信息。
    sections = []
    for heading in body.find_all("h2"):
        section = heading.find_parent("section")
        sections.append({
            "title": heading.get_text(" ", strip=True),
            "anchor": section.get("id") if section else None,
        })
    title = body.find("h1")
    metadata = {
        "title": title.get_text(" ", strip=True) if title else source.stem,
        "source_file": source.name,
        "source_path": str(source.resolve()),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "sections": sections,
        "table_count": len(body.find_all("table")),
        "image_count": len(body.find_all("img")),
        "images": [{"alt": img.get("alt", ""), "src": img.get("src", "")}
                   for img in body.find_all("img")],
    }

    # 4. 转换并保存。图片只保留原链接，这里不会联网下载或识图。
    markdown = markdownify(str(body), heading_style="ATX", bullets="-").strip()
    markdown = f"> 来源：{source.name}\n\n{markdown}\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / f"{source.stem}.md"
    metadata_path = output_dir / f"{source.stem}.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return markdown_path, metadata_path, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="原 HTML 文件")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="结果保存目录")
    args = parser.parse_args()
    try:
        markdown_path, metadata_path, metadata = convert_html(args.source, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"转换失败：{exc}\n")
    print(f"Markdown：{markdown_path.resolve()}")
    print(f"来源信息：{metadata_path.resolve()}")
    print(f"保留 {len(metadata['sections'])} 个章节、{metadata['table_count']} 张表格、"
          f"{metadata['image_count']} 个图片链接。")


if __name__ == "__main__":
    main()
