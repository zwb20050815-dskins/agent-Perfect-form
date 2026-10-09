"""第三课 3.2：把知识块转成向量，再按意思检索；本课不生成回答。"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = PROJECT_DIR / "data/chunks/银行会计重点笔记.chunks.json"


class LessonError(Exception):
    """可直接展示的本地提示，不含服务商返回的原始信息。"""


def read_config() -> dict:
    load_dotenv(PROJECT_DIR / ".env")
    get = lambda name: os.getenv(name, "").strip()
    base, key = get("EMBEDDING_BASE_URL"), get("EMBEDDING_API_KEY")
    # 用另一家服务时，地址和密钥必须一起填写。
    if bool(base) != bool(key):
        raise LessonError("EMBEDDING_BASE_URL 和 EMBEDDING_API_KEY 请一起填写，或一起留空。")
    base, key = base or get("CHAT_BASE_URL"), key or get("CHAT_API_KEY")
    model = get("EMBEDDING_MODEL")
    if not base or not key or not model:
        raise LessonError("请在本项目 .env 填好 CHAT_BASE_URL、CHAT_API_KEY、EMBEDDING_MODEL。")
    try:
        url = urlsplit(base)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment):
            raise ValueError
    except ValueError:
        raise LessonError("Embedding 地址应为不含密码或查询参数的 HTTPS 基础地址。") from None
    if url.path.rstrip("/").endswith(("/embeddings", "/chat/completions")):
        raise LessonError("请填写 API 基础地址，通常以 /v1 结尾，不加 /embeddings。")
    return {"base_url": base.rstrip("/"), "api_key": key, "model": model}


def load_chunks(path: Path) -> list[dict]:
    chunks = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(chunks, list) or not chunks:
        raise LessonError("切块文件必须是非空列表，请先运行 lesson03a.py。")
    ids = set()
    for chunk in chunks:
        for field in ("chunk_id", "source_file", "source_path", "text"):
            if not isinstance(chunk.get(field), str) or not chunk[field].strip():
                raise LessonError("知识块缺少有效的 ID、来源或正文。")
        headings = chunk.get("heading_path")
        if not isinstance(headings, list) or not headings or not all(
                isinstance(h, str) and h.strip() for h in headings):
            raise LessonError("知识块缺少标题路径。")
        if chunk["chunk_id"] in ids:
            raise LessonError("知识块的 chunk_id 有重复，请重新切块。")
        ids.add(chunk["chunk_id"])
    return chunks


def embedding_text(chunk: dict) -> str:
    # 标题提供章节背景，正文提供具体知识；两部分一起参与检索。
    return " > ".join(chunk["heading_path"]) + "\n\n" + chunk["text"]


def unit_vector(vector: list, dimension: int | None = None) -> list[float]:
    """把向量的长度变成 1；之后两个向量点乘，就是余弦相似度。"""
    if not isinstance(vector, list) or not vector or (
            dimension is not None and len(vector) != dimension):
        raise LessonError("向量为空或维度不一致，请检查模型并重新建索引。")
    if any(type(n) not in (int, float) or not math.isfinite(n) for n in vector):
        raise LessonError("向量包含无效数字。")
    length = math.hypot(*vector)
    if not math.isfinite(length) or length == 0:
        raise LessonError("向量长度无效。")
    return [n / length for n in vector]


def index_identity(chunks: list[dict], config: dict) -> dict:
    # 内容、来源或模型变了，旧向量就不能直接复用；密钥不写入索引。
    content = json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"version": 1, "model": config["model"], "base_url": config["base_url"],
            "chunks_sha256": hashlib.sha256(content).hexdigest()}


def read_index(path: Path, chunks: list[dict], config: dict) -> dict:
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("identity") != index_identity(chunks, config):
        raise LessonError("知识块或模型配置已变，请先运行 lesson03b.py index。")
    rows, dimension = index["rows"], index["dimension"]
    if type(dimension) is not int or dimension <= 0 or len(rows) != len(chunks):
        raise LessonError("索引的数量或维度不正确。")
    for row, chunk in zip(rows, chunks):
        if {k: v for k, v in row.items() if k != "embedding"} != chunk:
            raise LessonError("索引和当前知识块不对应，请重新建索引。")
        unit_vector(row["embedding"], dimension)
    return index


def build_index(chunks: list[dict], config: dict, model: OpenAIEmbeddings,
                path: Path, rebuild: bool) -> None:
    if path.exists() and not rebuild:
        try:
            read_index(path, chunks, config)
        except (OSError, LessonError, ValueError, KeyError, TypeError, AttributeError):
            print("已有索引需要更新，将重新生成向量。")
        else:
            print(f"已复用 {len(chunks)} 个知识块的索引；没有调用 API。")
            return

    print(f"正在把 {len(chunks)} 个知识块的标题和正文发送给 Embedding 服务……", flush=True)
    vectors = model.embed_documents([embedding_text(chunk) for chunk in chunks])
    if len(vectors) != len(chunks) or not vectors:
        raise LessonError("返回的向量数量与知识块数量不一致。")
    dimension = len(vectors[0])
    for vector in vectors:
        unit_vector(vector, dimension)
    index = {"identity": index_identity(chunks, config), "dimension": dimension,
             "rows": [{**chunk, "embedding": vector} for chunk, vector in zip(chunks, vectors)]}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)  # 完整生成后再替换，失败时保留原来的索引。
    print(f"已保存 {len(chunks)} 个向量，每个 {dimension} 维：{path.resolve()}")


def search(index: dict, question: str, model: OpenAIEmbeddings, top_k: int) -> list:
    # 问题也要用同一个模型转成向量，才能和笔记里的向量比较。
    question_vector = unit_vector(model.embed_query(question), index["dimension"])
    results = []
    for row in index["rows"]:
        chunk_vector = unit_vector(row["embedding"], index["dimension"])
        score = sum(a * b for a, b in zip(question_vector, chunk_vector))
        results.append((score, row))
    return sorted(results, key=lambda item: item[0], reverse=True)[:top_k]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("index", "search"), default="index")
    parser.add_argument("question", nargs="?", help="search 时输入的问题")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课 3.1 的切块文件")
    parser.add_argument("--top-k", type=int, default=3, help="显示几个片段，默认 3")
    parser.add_argument("--check", action="store_true", help="只检查本地配置和知识块，不联网")
    parser.add_argument("--rebuild", action="store_true", help="index 时强制重建")
    args = parser.parse_args()
    if args.top_k <= 0:
        parser.error("--top-k 必须大于 0。")
    if args.action == "search" and not args.check and not (args.question or "").strip():
        parser.error("search 后面请填写问题。")
    if (args.action == "index" and args.question) or (args.action == "search" and args.rebuild):
        parser.error("问题只用于 search；--rebuild 只用于 index。")
    try:
        config = read_config()
        chunks = load_chunks(args.source)
        path = PROJECT_DIR / "data/vectors" / (args.source.stem.removesuffix(".chunks") + ".vectors.json")
        if args.check:
            print(f"本地配置和 {len(chunks)} 个知识块检查通过；尚未验证 API 或模型权限。")
            return 0
        # 同一实例负责笔记和问题的向量化。直接发送文字，避免按其他模型的规则切 token。
        with httpx.Client(follow_redirects=False) as client:
            # 这里 chunk_size=10 表示每批发送 10 块，与上一课的 600 字符无关。
            model = OpenAIEmbeddings(
                **config, check_embedding_ctx_length=False, chunk_size=10,
                model_kwargs={"encoding_format": "float"}, max_retries=0,
                request_timeout=60, http_client=client,
            )
            if args.action == "index":
                build_index(chunks, config, model, path, args.rebuild)
            else:
                index = read_index(path, chunks, config)
                results = search(index, args.question.strip(), model, args.top_k)
                print("以下是笔记原文；分数用于排序，不是答案正确率。")
                for rank, (score, row) in enumerate(results, 1):
                    print(f"\n{rank}. 相似度 {score:.4f} | {row['chunk_id']}")
                    print("标题：" + " > ".join(row["heading_path"]))
                    print("来源：" + row["source_file"])
                    print(row["text"])
        return 0
    except FileNotFoundError:
        print("缺少文件：请先运行 lesson03a.py，再运行 lesson03b.py index。")
    except LessonError as exc:
        print(f"未完成：{exc}")
    except (ValueError, KeyError, TypeError, AttributeError):
        # 只显示本地排查步骤，不输出可能包含密钥的配置或服务商响应。
        print("配置、知识块或索引格式不正确。检查 .env、切块文件；必要时用 index --rebuild 重建。")
    except Exception as exc:
        print(f"执行失败（{type(exc).__name__}）。请检查网络、地址、Embedding 模型权限和额度。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
