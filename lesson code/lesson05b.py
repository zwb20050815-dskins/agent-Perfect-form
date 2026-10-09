"""第五课 5.2：用条件边决定继续回答，还是提示资料未通过筛选。"""

import argparse
import math
from pathlib import Path
from typing import Literal

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from lesson01 import read_config as read_chat_config
from lesson03b import (
    DEFAULT_SOURCE, PROJECT_DIR, LessonError, load_chunks, read_index,
    read_config as read_embedding_config, search as vector_search,
)
from lesson03c import build_messages, check_answer, show_sources
from lesson04a import keyword_search
from lesson04b import rrf_fuse
from lesson04c import read_rerank_config, rerank_candidates
from lesson05a import AgentState, Services


class RoutedState(AgentState, total=False):
    min_score: float  # 本次运行的筛选门槛，不代表答案正确率。


def retrieve(state: RoutedState, runtime: Runtime[Services]) -> dict:
    print("[retrieve] 向量检索 + BM25 + RRF……", flush=True)
    services = runtime.context
    vector_results = vector_search(services.index, state["question"], services.embedding_model, 5)
    keyword_results = keyword_search(services.chunks, state["question"], 5)
    candidates = rrf_fuse(vector_results, keyword_results, top_k=6)
    print(f"    得到 {len(candidates)} 块候选资料", flush=True)
    return {"candidates": candidates}


def rerank(state: RoutedState, runtime: Runtime[Services]) -> dict:
    print("[rerank] 重排并选出最多 3 块……", flush=True)
    services = runtime.context
    selected = rerank_candidates(state["question"], state["candidates"],
                                 services.rerank_config, services.client, top_k=3)
    return {"selected": selected}


def filter_selected(state: RoutedState) -> dict:
    """只更新 selected；question、candidates、min_score 会继续保留。"""
    threshold = state["min_score"]
    selected = [row for row in state["selected"] if row["rerank_score"] >= threshold]
    print(f"[filter] 门槛 {threshold:g}；{len(state['selected'])} 块中有 {len(selected)} 块通过", flush=True)
    for row in state["selected"]:
        decision = "保留" if row["rerank_score"] >= threshold else "过滤"
        print(f"    {row['chunk']['chunk_id']} | {row['rerank_score']:.6f} | {decision}", flush=True)
    return {"selected": selected}


def choose_next(state: RoutedState) -> Literal["answer", "insufficient"]:
    """路由函数只返回下一站的名称，不修改 State，也不调用模型。"""
    if state["selected"]:
        print("[route] 有资料通过筛选 → answer", flush=True)
        return "answer"
    print("[route] 没有资料通过筛选 → insufficient", flush=True)
    return "insufficient"


def insufficient(state: RoutedState) -> dict:
    print("[insufficient] 直接返回提示，没有调用聊天模型。", flush=True)
    return {"answer_text": "本次没有资料通过设定的相关性筛选，暂不生成模型回答。请换一种问法，或检查笔记和检索结果。"}


def answer(state: RoutedState, runtime: Runtime[Services]) -> dict:
    print("[answer] Qwen3 根据筛选后的原文回答……", flush=True)
    # 筛选可能减少片段数，引用按剩下的资料重新从 [1] 编号。
    sources = [(row["rerank_score"], row["chunk"]) for row in state["selected"]]
    response = runtime.context.chat_model.invoke(build_messages(state["question"], sources))
    if response.response_metadata.get("finish_reason") == "length":
        raise LessonError("回答达到长度上限而中断，请缩小问题范围后重试。")
    check_answer(response.content, len(sources))
    return {"answer_text": response.content.strip()}


def build_graph(retrieve_node=retrieve, rerank_node=rerank, answer_node=answer):
    # 三个可替换的节点用于离线演示；正常运行时使用上面的真实函数。
    builder = StateGraph(RoutedState, context_schema=Services)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("rerank", rerank_node)
    builder.add_node("filter", filter_selected)
    builder.add_node("answer", answer_node)
    builder.add_node("insufficient", insufficient)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "filter")
    builder.add_conditional_edges("filter", choose_next, {
        "answer": "answer", "insufficient": "insufficient",
    })
    # filter 后只使用条件边；不要再同时接一条直达 answer 的普通边。
    builder.add_edge("answer", END)
    builder.add_edge("insufficient", END)
    return builder.compile()


def run_demo(min_score: float = 0.5) -> None:
    print("离线人工演示：使用固定分数，不读取你的笔记或配置，也不调用任何模型。")

    def demo_retrieve(state):
        return {"candidates": [{"chunk": {"chunk_id": "演示块", "text": "人工演示文字"}}]}

    def demo_rerank(state):
        score = 0.8 if state["question"] == "高相关演示" else 0.2
        return {"selected": [{**state["candidates"][0], "rerank_score": score}]}

    def demo_answer(state):
        print("[answer] 进入演示回答节点，没有调用 Qwen3。")
        return {"answer_text": "【人工演示回答】有资料通过筛选，可以进入回答节点。"}

    graph = build_graph(demo_retrieve, demo_rerank, demo_answer)
    for question in ("高相关演示", "低相关演示"):
        print(f"\n--- {question} ---")
        result = graph.invoke({"question": question, "min_score": min_score})
        print(result["answer_text"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="试算平衡能发现所有记账错误吗？")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课的切块文件")
    parser.add_argument("--min-score", type=float, default=0.5, help="演示用筛选门槛，默认 0.5，需按实际数据调整")
    parser.add_argument("--show-context", action="store_true", help="显示最终交给 Qwen3 的原文")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查配置、图和索引，不联网")
    mode.add_argument("--graph", action="store_true", help="输出实际图的 Mermaid 文本，不读配置")
    mode.add_argument("--demo", action="store_true", help="用固定分数演示条件路由，不联网")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    if not math.isfinite(args.min_score):
        parser.error("--min-score 必须是有限数字。")

    try:
        if args.demo:
            run_demo(args.min_score)
            return 0
        graph = build_graph()
        if args.graph:
            print(graph.get_graph().draw_mermaid())
            return 0
        try:
            chat_config = read_chat_config()
        except ValueError as exc:
            raise LessonError(str(exc)) from None
        embedding_config, rerank_config = read_embedding_config(), read_rerank_config()
        chunks = load_chunks(args.source)
        index_path = PROJECT_DIR / "data/vectors" / (args.source.stem.removesuffix(".chunks") + ".vectors.json")
        index = read_index(index_path, chunks, embedding_config)
        if args.check:
            print(f"条件路由图、配置、{len(chunks)} 个知识块与索引检查通过；尚未验证云 API。")
            return 0
        with httpx.Client(follow_redirects=False) as client:
            services = Services(
                chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                embedding_model=OpenAIEmbeddings(
                    **embedding_config, check_embedding_ctx_length=False, chunk_size=10,
                    model_kwargs={"encoding_format": "float"}, max_retries=0,
                    request_timeout=60, http_client=client,
                ),
                chat_model=ChatOpenAI(
                    model=chat_config["CHAT_MODEL"], base_url=chat_config["CHAT_BASE_URL"],
                    api_key=chat_config["CHAT_API_KEY"], temperature=0, max_tokens=900,
                    timeout=60, max_retries=0, http_client=client,
                ),
            )
            result = graph.invoke({"question": args.question.strip(), "min_score": args.min_score}, context=services)
        print("\n结果：\n" + result["answer_text"])
        if result["selected"]:
            sources = [(row["rerank_score"], row["chunk"]) for row in result["selected"]]
            show_sources(sources, show_context=args.show_context)
        return 0
    except FileNotFoundError:
        print("缺少知识块或索引，请先完成第三课的切块和建索引。")
    except LessonError as exc:
        print(f"未完成：{exc}")
    except httpx.HTTPStatusError as exc:
        print(f"接口调用失败（HTTP {exc.response.status_code}）；请检查最后一个节点对应的服务配置与额度。")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("流程未完成：本地数据或接口返回格式不正确，请结合最后一个节点的日志检查。")
    except Exception as exc:
        print(f"流程未完成（{type(exc).__name__}）；请结合最后一个节点的日志检查网络与模型权限。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
