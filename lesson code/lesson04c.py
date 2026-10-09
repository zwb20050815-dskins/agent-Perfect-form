"""第四课 4.3：用专门模型重排候选资料，可选让 Qwen3 根据结果回答。"""

import argparse
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lesson01 import read_config as read_chat_config
from lesson03b import (
    DEFAULT_SOURCE, PROJECT_DIR, LessonError, embedding_text, load_chunks,
    read_config as read_embedding_config, read_index, search as vector_search,
)
from lesson03c import build_messages, check_answer, show_sources
from lesson04a import keyword_search
from lesson04b import rrf_fuse, show_fused


def read_rerank_config() -> dict:
    load_dotenv(PROJECT_DIR / ".env")
    get = lambda name: os.getenv(name, "").strip()
    model, url = get("RERANK_MODEL"), get("RERANK_URL")
    if not model or not url:
        raise LessonError("请在 .env 填写 RERANK_MODEL 和完整的 RERANK_URL。")
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or not parsed.path.strip("/")):
            raise ValueError
        origin = (parsed.scheme, parsed.hostname, parsed.port or 443)
        key = get("RERANK_API_KEY")
        if not key:
            chat = urlsplit(get("CHAT_BASE_URL"))
            if origin != (chat.scheme, chat.hostname, chat.port or 443):
                raise LessonError("重排与聊天服务地址不同，请单独填写 RERANK_API_KEY。")
            key = get("CHAT_API_KEY")
    except ValueError:
        raise LessonError("RERANK_URL 应为不含密码、查询参数或片段的完整 HTTPS 接口地址。") from None
    if not key:
        raise LessonError("请配置 RERANK_API_KEY；同一服务也可沿用 CHAT_API_KEY。")
    return {"model": model, "url": url, "api_key": key}


def map_rerank_results(payload: dict, candidates: list[dict], top_k: int) -> list[dict]:
    """按 API 返回的 index 找回原候选，原文和来源一起跟随。"""
    try:
        rows = payload["output"]["results"]
    except (KeyError, TypeError):
        raise LessonError("重排响应缺少 output.results，请确认接口使用本课的原生格式。") from None
    # 请求了全部候选的分数；缺项不能被默默当成完整重排。
    if not isinstance(rows, list) or len(rows) != len(candidates):
        raise LessonError("重排返回数量不完整；本次不把原 RRF 结果冒充为重排结果。")
    ranked, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise LessonError("重排结果条目格式不正确。")
        index, score = row.get("index"), row.get("relevance_score")
        if type(index) is not int or not 0 <= index < len(candidates) or index in seen:
            raise LessonError("重排返回的候选索引越界、重复或格式不正确。")
        if type(score) not in (int, float) or not math.isfinite(score):
            raise LessonError("重排返回了无效的相关性分数。")
        seen.add(index)
        ranked.append({**candidates[index], "rrf_rank": index + 1, "rerank_score": float(score)})
    # 用模型分数重新排序；不与 RRF 分数相加。同分时保留之前的 RRF 顺序。
    return sorted(ranked, key=lambda item: (-item["rerank_score"], item["rrf_rank"]))[:top_k]


def rerank_candidates(question: str, candidates: list[dict], config: dict,
                      client: httpx.Client, top_k: int = 3) -> list[dict]:
    if top_k <= 0:
        raise LessonError("top_k 必须大于 0。")
    if not candidates:
        return []
    # 用已验证的原生接口：模型读取“问题 + 标题与正文”，不会读取向量或文件路径。
    response = client.post(config["url"], headers={"Authorization": "Bearer " + config["api_key"]},
                           json={"model": config["model"],
                                 "input": {"query": question,
                                           "documents": [embedding_text(row["chunk"]) for row in candidates]},
                                 "parameters": {"top_n": len(candidates), "return_documents": False}},
                           timeout=60)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        raise LessonError("重排接口没有返回有效 JSON。") from None
    return map_rerank_results(payload, candidates, top_k)


def show_reranked(results: list[dict], show_context: bool) -> None:
    print("\n重排后的资料（得分不是答案正确率）：")
    for rank, row in enumerate(results, 1):
        chunk = row["chunk"]
        print(f"[{rank}] {chunk['chunk_id']} | 原 RRF 第 {row['rrf_rank']} 名"
              f" | 重排分数 {row['rerank_score']:.6f}")
        print("来源：" + chunk["source_file"])
        print("章节：" + " > ".join(chunk["heading_path"]))
        if show_context:
            print(chunk["text"] + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="科目和借贷方向都正确，只是金额少写了，用哪种更正方法？")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课的切块文件")
    parser.add_argument("--candidates", type=int, default=5, help="两路各取几个候选，默认 5")
    parser.add_argument("--rerank-candidates", type=int, default=6, help="RRF 后最多送几块去重排，默认 6")
    parser.add_argument("--top-k", type=int, default=3, help="重排后最多保留几块，默认 3")
    parser.add_argument("--check", action="store_true", help="只检查本地配置和索引，不联网")
    parser.add_argument("--show-context", action="store_true", help="显示重排选中的笔记原文")
    parser.add_argument("--answer", action="store_true", help="再调用 Qwen3，根据重排结果回答")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    if min(args.candidates, args.rerank_candidates, args.top_k) <= 0:
        parser.error("三个数量参数都必须大于 0。")
    if args.top_k > args.rerank_candidates:
        parser.error("--top-k 不能大于 --rerank-candidates。")

    stage = "本地检查"
    try:
        embedding_config = read_embedding_config()
        rerank_config = read_rerank_config()
        chat_config = None
        if args.answer:
            try:
                chat_config = read_chat_config()
            except ValueError as exc:
                raise LessonError(str(exc)) from None
        chunks = load_chunks(args.source)
        index_path = PROJECT_DIR / "data/vectors" / (args.source.stem.removesuffix(".chunks") + ".vectors.json")
        index = read_index(index_path, chunks, embedding_config)
        if args.check:
            print(f"配置、{len(chunks)} 个知识块与索引检查通过；尚未验证云 API。")
            return 0

        with httpx.Client(follow_redirects=False) as client:
            stage = "检索笔记"
            print("1. 正在进行两路检索与 RRF 融合……", flush=True)
            embedding_model = OpenAIEmbeddings(
                **embedding_config, check_embedding_ctx_length=False, chunk_size=10,
                model_kwargs={"encoding_format": "float"}, max_retries=0,
                request_timeout=60, http_client=client,
            )
            vector_results = vector_search(index, args.question.strip(), embedding_model, args.candidates)
            keyword_results = keyword_search(chunks, args.question.strip(), args.candidates)
            # 此时先保留 6 个候选，把最后选 3 个的工作留给重排模型。
            candidates = rrf_fuse(vector_results, keyword_results, args.rerank_candidates)
            show_fused(candidates, show_text=False)
            if not candidates:
                print("没有可重排的候选资料。")
                return 0
            stage = "模型重排"
            print(f"\n2. 正在把问题和 {len(candidates)} 个候选的文字交给重排模型……", flush=True)
            ranked = rerank_candidates(args.question.strip(), candidates, rerank_config, client, args.top_k)
            show_reranked(ranked, args.show_context)

            if args.answer:
                stage = "生成回答"
                print("\n3. 正在让 Qwen3 根据重排后的资料回答……", flush=True)
                chat = ChatOpenAI(
                    model=chat_config["CHAT_MODEL"], base_url=chat_config["CHAT_BASE_URL"],
                    api_key=chat_config["CHAT_API_KEY"], temperature=0, max_tokens=900,
                    timeout=60, max_retries=0, http_client=client,
                )
                # 按最终顺序重新编号 [1]、[2]、[3]，继续沿用第三课的回答规则。
                final_sources = [(row["rerank_score"], row["chunk"]) for row in ranked]
                response = chat.invoke(build_messages(args.question.strip(), final_sources))
                if response.response_metadata.get("finish_reason") == "length":
                    raise LessonError("回答达到长度上限而中断，请缩小问题范围后重试。")
                check_answer(response.content, len(final_sources))
                print("\n回答：\n" + response.content.strip())
                show_sources(final_sources, show_context=False)
        return 0
    except FileNotFoundError:
        print("缺少知识块或索引，请先运行 lesson03a.py，再运行 lesson03b.py index。")
    except LessonError as exc:
        print(f"未完成：{exc}")
    except httpx.HTTPStatusError as exc:
        print(f"{stage}失败（HTTP {exc.response.status_code}）；请检查重排地址、模型 ID、密钥和额度。")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(f"{stage}失败：本地数据或接口返回格式不正确。")
    except Exception as exc:
        print(f"{stage}失败（{type(exc).__name__}）；请检查网络、模型权限和额度。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
