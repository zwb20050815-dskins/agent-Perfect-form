"""第五课 5.1：用 LangGraph 连接检索、重排和回答三个节点。"""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from lesson01 import read_config as read_chat_config
from lesson03b import (
    DEFAULT_SOURCE, PROJECT_DIR, LessonError, load_chunks, read_index,
    read_config as read_embedding_config, search as vector_search,
)
from lesson03c import INSUFFICIENT, build_messages, check_answer, show_sources
from lesson04a import keyword_search
from lesson04b import rrf_fuse
from lesson04c import read_rerank_config, rerank_candidates


# State 是这一次问答的数据。节点只需返回自己更新的字段。
class AgentState(TypedDict, total=False):
    question: str
    candidates: list[dict]  # 检索后，最多 6 块
    selected: list[dict]    # 重排后，最多 3 块
    answer_text: str


@dataclass
class Services:
    """供节点共用的资料与连接；这些不是问答 State。"""
    chunks: list[dict]
    index: dict
    embedding_model: OpenAIEmbeddings
    rerank_config: dict
    client: httpx.Client
    chat_model: ChatOpenAI


def retrieve(state: AgentState, runtime: Runtime[Services]) -> dict:
    print("[1/3 retrieve] 向量检索 + BM25 + RRF……", flush=True)
    services = runtime.context
    question = state["question"]
    vector_results = vector_search(services.index, question, services.embedding_model, 5)
    keyword_results = keyword_search(services.chunks, question, 5)
    candidates = rrf_fuse(vector_results, keyword_results, top_k=6)
    print(f"    更新 State.candidates：{len(candidates)} 块候选资料", flush=True)
    return {"candidates": candidates}


def rerank(state: AgentState, runtime: Runtime[Services]) -> dict:
    print("[2/3 rerank] 重排模型给候选原文打分……", flush=True)
    services = runtime.context
    selected = rerank_candidates(
        state["question"], state["candidates"], services.rerank_config,
        services.client, top_k=3,
    )
    print(f"    更新 State.selected：{len(selected)} 块最终资料", flush=True)
    return {"selected": selected}


def answer(state: AgentState, runtime: Runtime[Services]) -> dict:
    print("[3/3 answer] Qwen3 根据最终资料回答……", flush=True)
    if not state["selected"]:
        # 没有候选时直接说明资料不足，不调用聊天模型。
        return {"answer_text": INSUFFICIENT}
    sources = [(row["rerank_score"], row["chunk"]) for row in state["selected"]]
    response = runtime.context.chat_model.invoke(build_messages(state["question"], sources))
    if response.response_metadata.get("finish_reason") == "length":
        raise LessonError("回答达到长度上限而中断，请缩小问题范围后重试。")
    check_answer(response.content, len(sources))
    return {"answer_text": response.content.strip()}


def build_graph():
    # 先声明 State 的结构，再登记节点，最后用边连接执行顺序。
    builder = StateGraph(AgentState, context_schema=Services)
    builder.add_node("retrieve", retrieve)
    builder.add_node("rerank", rerank)
    builder.add_node("answer", answer)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "answer")
    builder.add_edge("answer", END)
    return builder.compile()  # 组装为可以执行的图；这里还没有调用模型。


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="试算平衡能发现所有记账错误吗？")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课的切块文件")
    parser.add_argument("--show-context", action="store_true", help="显示最终交给 Qwen3 的原文")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查依赖、图、配置和索引，不联网")
    mode.add_argument("--graph", action="store_true", help="输出 Mermaid 流程图文本，不读配置或调用模型")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")

    try:
        graph = build_graph()
        if args.graph:
            print(graph.get_graph().draw_mermaid())
            return 0

        # 下面继续使用前面课程的配置和模型连接，不需要新增密钥。
        try:
            chat_config = read_chat_config()
        except ValueError as exc:
            raise LessonError(str(exc)) from None
        embedding_config = read_embedding_config()
        rerank_config = read_rerank_config()
        chunks = load_chunks(args.source)
        index_path = PROJECT_DIR / "data/vectors" / (args.source.stem.removesuffix(".chunks") + ".vectors.json")
        index = read_index(index_path, chunks, embedding_config)
        if args.check:
            print(f"LangGraph 图、配置、{len(chunks)} 个知识块与索引检查通过；尚未验证云 API。")
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
            # invoke 才会从 START 开始执行。初始 State 只需用户问题。
            result = graph.invoke({"question": args.question.strip()}, context=services)

        print("\n回答：\n" + result["answer_text"])
        sources = [(row["rerank_score"], row["chunk"]) for row in result["selected"]]
        if sources:
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
        # 不输出原始异常正文、密钥或请求头；失败不会继续生成回答。
        print(f"流程未完成（{type(exc).__name__}）；请结合最后一个节点的日志检查网络与模型权限。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
