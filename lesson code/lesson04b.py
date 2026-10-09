"""第四课 4.2：把向量检索与 BM25 的排名，用 RRF 合并。"""

import argparse
from pathlib import Path

import httpx
from langchain_openai import OpenAIEmbeddings

from lesson03b import (
    DEFAULT_SOURCE, PROJECT_DIR, LessonError, load_chunks, read_config,
    read_index, search as vector_search,
)
from lesson04a import keyword_search

RRF_K = 60


def rrf_fuse(vector_results: list, keyword_results: list,
             top_k: int = 3, k: int = RRF_K) -> list[dict]:
    """输入两份已排好序的结果；按块编号去重，累加排名贡献。"""
    if top_k <= 0 or k <= 0:
        raise LessonError("top_k 和 RRF 的 k 必须大于 0。")
    merged = {}
    for route, results in (("vector", vector_results), ("keyword", keyword_results)):
        seen = set()
        rank = 0
        for original_score, chunk in results:
            chunk_id = chunk["chunk_id"]
            # 向量检索的记录多一个 embedding 字段；融合时保留原文和来源即可。
            original = {name: value for name, value in chunk.items() if name != "embedding"}
            if chunk_id in merged and merged[chunk_id]["chunk"] != original:
                raise LessonError("同一个块编号对应了不同内容，请核对知识块与索引。")
            if chunk_id in seen:
                continue  # 同一路重复出现，只算一次。
            seen.add(chunk_id)
            rank += 1  # 排名从 1 开始。
            if chunk_id not in merged:
                merged[chunk_id] = {"chunk": original, "score": 0.0,
                                    "vector_rank": None, "keyword_rank": None}
            merged[chunk_id]["score"] += 1 / (k + rank)
            merged[chunk_id][f"{route}_rank"] = rank
    # 同一个块在两路出现，会得到两份贡献；最终列表只保留一条。
    # 同分时按编号固定顺序，方便重复观察；编号本身不代表相关性。
    return sorted(merged.values(), key=lambda row: (-row["score"], row["chunk"]["chunk_id"]))[:top_k]


def show_rankings(vector_results: list, keyword_results: list) -> None:
    for name, results in (("向量检索候选", vector_results), ("BM25 检索候选", keyword_results)):
        print(f"\n{name}：")
        if not results:
            print("（本路没有候选）")
        for rank, (score, chunk) in enumerate(results, 1):
            print(f"{rank}. {chunk['chunk_id']} | 原始分数 {score:.4f} | {chunk['heading_path'][-1]}")


def show_fused(results: list[dict], show_text: bool = True) -> None:
    print("\nRRF 融合结果：")
    print("名次 | 块编号 | 向量名次 | BM25 名次 | RRF 分数")
    for rank, row in enumerate(results, 1):
        print(f"{rank} | {row['chunk']['chunk_id']} | {row['vector_rank'] or '—'}"
              f" | {row['keyword_rank'] or '—'} | {row['score']:.6f}")
    print("‘—’表示不在该路取出的候选里；分数只用于排序，不是答案正确率。")
    if show_text:
        for rank, row in enumerate(results, 1):
            chunk = row["chunk"]
            print(f"\n[{rank}] {chunk['source_file']} | {chunk['chunk_id']}")
            print("章节：" + " > ".join(chunk["heading_path"]))
            print(chunk["text"])


def run_demo() -> None:
    """用人工排名演示融合；不读笔记或配置，也不调用 API。"""
    chunks = {name: {"chunk_id": name, "source_file": "演示数据", "source_path": "演示数据",
                     "heading_path": [f"演示块 {name}"], "text": name, "char_count": 1}
              for name in "ABCD"}
    vector_results = [(0.9, chunks["A"]), (0.8, chunks["B"]), (0.7, chunks["C"])]
    keyword_results = [(12.0, chunks["B"]), (8.0, chunks["D"]), (5.0, chunks["A"])]
    print("以下排名是人工设定的算法演示，不是你的笔记检索结果。")
    show_rankings(vector_results, keyword_results)
    show_fused(rrf_fuse(vector_results, keyword_results), show_text=False)
    print("\nB 的得分 = 1/(60+2) + 1/(60+1)，两路贡献相加后排在第一。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="补充登记法适用于什么情况？")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课的切块文件")
    parser.add_argument("--candidates", type=int, default=5, help="每路最多取几个候选，默认 5")
    parser.add_argument("--top-k", type=int, default=3, help="融合后最多显示几个块，默认 3")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只检查本地配置、知识块和索引")
    mode.add_argument("--demo", action="store_true", help="看人工排名的融合演示，不联网")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    if args.candidates <= 0 or args.top_k <= 0:
        parser.error("--candidates 和 --top-k 必须大于 0。")
    if args.demo:
        run_demo()
        return 0

    stage = "读取本地配置与索引"
    try:
        config = read_config()
        chunks = load_chunks(args.source)
        index_path = PROJECT_DIR / "data/vectors" / (args.source.stem.removesuffix(".chunks") + ".vectors.json")
        index = read_index(index_path, chunks, config)
        if args.check:
            print(f"依赖、Embedding 配置、{len(chunks)} 个知识块与索引检查通过；尚未验证云 API。")
            return 0

        stage = "检索笔记"
        print(f"正在检索：每路最多取 {args.candidates} 个候选……", flush=True)
        with httpx.Client(follow_redirects=False) as client:
            embedding_model = OpenAIEmbeddings(
                **config, check_embedding_ctx_length=False, chunk_size=10,
                model_kwargs={"encoding_format": "float"}, max_retries=0,
                request_timeout=60, http_client=client,
            )
            # 向量这一路只给问题生成新向量，笔记继续复用已有向量。
            vector_results = vector_search(index, args.question.strip(), embedding_model, args.candidates)
        # 关键词检索与 RRF 都在本地计算。
        keyword_results = keyword_search(chunks, args.question.strip(), args.candidates)
        fused_results = rrf_fuse(vector_results, keyword_results, args.top_k)
        show_rankings(vector_results, keyword_results)
        show_fused(fused_results)
        return 0
    except FileNotFoundError:
        print("缺少知识块或索引。请先运行 lesson03a.py，再运行 lesson03b.py index。")
    except LessonError as exc:
        print(f"未完成：{exc}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("文件或数据格式不正确，请检查知识块和索引。")
    except Exception as exc:
        print(f"{stage}失败（{type(exc).__name__}）；请检查网络、Embedding 模型权限与额度。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
