"""第六课 6.2：使用 Redis 保存会话状态，让不同 Python 进程接着聊。"""

import argparse
from contextlib import contextmanager
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.redis import RedisSaver
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from lesson01 import read_config as read_chat_config
from lesson03b import (
    DEFAULT_SOURCE, PROJECT_DIR, LessonError, load_chunks, read_index,
    read_config as read_embedding_config,
)
from lesson03c import show_sources
from lesson04c import read_rerank_config
from lesson05a import Services
from lesson06a import build_graph

SESSION_PREFIX = "knowledge-agent:lesson06b:v1:"
DEFAULT_REDIS_URL = "redis://127.0.0.1:6380/0"


def read_redis_url() -> str:
    load_dotenv(PROJECT_DIR / ".env")
    url = os.getenv("REDIS_URL", "").strip() or DEFAULT_REDIS_URL
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("redis", "rediss") or not parsed.hostname
                or parsed.query or parsed.fragment or parsed.path not in ("", "/", "/0")
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
            raise ValueError
    except ValueError:
        raise LessonError("REDIS_URL 格式不正确；本课使用 Redis 的 0 号数据库。") from None
    return url


def session_config(session_id: str) -> dict:
    # 项目前缀避免与别的练习混用会话；checkpoint_ns 留给 LangGraph 自己管理。
    return {"configurable": {"thread_id": SESSION_PREFIX + session_id}}


@contextmanager
def open_redis_graph(url: str):
    with Redis.from_url(url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5,
                        retry=Retry(NoBackoff(), 0), retry_on_timeout=False) as client:
        client.ping()
        with RedisSaver.from_conn_string(redis_client=client) as saver:
            saver.setup()  # 创建或检查 RedisJSON / Search 所需的 checkpoint 索引。
            yield build_graph(checkpointer=saver)


def invoke_turn(graph, question: str, session_id: str, services: Services, min_score: float = 0.5):
    # 从 Redis 恢复未传入的 history；本轮问题和临时结果明确更新。
    inputs = {"user_question": question.strip(), "question": "", "min_score": min_score,
              "candidates": [], "selected": [], "answer_text": ""}
    return graph.invoke(inputs, config=session_config(session_id), context=services, durability="sync")


def show_history(graph, session_id: str) -> None:
    history = graph.get_state(session_config(session_id)).values.get("history", [])
    print(f"会话 {session_id}：最近 {len(history)} 轮已完成的问答。")
    for number, turn in enumerate(history, 1):
        print(f"{number}. 你：{turn['user_question']}\n   助手：{turn['answer']}")
    if history:
        print("历史中的引用编号只对应原来那一轮的资料。")


def report_error(exc: Exception) -> None:
    if isinstance(exc, RedisError):
        print(f"Redis 操作未完成（{type(exc).__name__}）；请检查容器与 REDIS_URL。程序不会改用内存保存。")
    elif isinstance(exc, LessonError):
        print(f"未完成：{exc}")
    elif isinstance(exc, FileNotFoundError):
        print("缺少知识块或索引，请先完成第三课。")
    elif isinstance(exc, httpx.HTTPStatusError):
        print(f"模型接口调用失败（HTTP {exc.response.status_code}）；请检查对应的服务配置与额度。")
    else:
        # 原始错误可能包含 Redis URL 或密钥，只展示异常类别。
        print(f"流程未完成（{type(exc).__name__}）；请结合最后一个节点的日志检查配置、数据与连接。")


def read_local_data(source: Path):
    try:
        chat_config = read_chat_config()
    except ValueError as exc:
        raise LessonError(str(exc)) from None
    embedding_config, rerank_config = read_embedding_config(), read_rerank_config()
    chunks = load_chunks(source)
    index_path = PROJECT_DIR / "data/vectors" / (source.stem.removesuffix(".chunks") + ".vectors.json")
    index = read_index(index_path, chunks, embedding_config)
    return chat_config, embedding_config, rerank_config, chunks, index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", nargs="*", help="可选：依次运行这些问题；不填则进入连续对话")
    parser.add_argument("--session", default="study", help="会话编号，重启后使用相同编号继续")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--show-context", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查本地配置与索引，不连接 Redis 或模型")
    mode.add_argument("--check-redis", action="store_true", help="连接 Redis 并初始化 checkpoint 索引，不调用模型")
    mode.add_argument("--history", action="store_true", help="从 Redis 读取本会话记录，不调用模型")
    mode.add_argument("--graph", action="store_true", help="只输出图结构，不连接 Redis 或模型")
    args = parser.parse_args()
    session_id = args.session.strip()
    if not 0 < len(session_id) <= 64 or any(not q.strip() for q in args.questions):
        parser.error("会话编号应为 1～64 字符，问题不能为空。")
    if not math.isfinite(args.min_score):
        parser.error("--min-score 必须是有限数字。")
    if args.questions and any((args.check, args.check_redis, args.history, args.graph)):
        parser.error("检查、查看历史或查看图时，不要同时传入问题。")
    try:
        if args.graph:
            # 仅组装并显示沿用的图结构，节点和保存器都不会执行。
            print(build_graph().get_graph().draw_mermaid())
            return 0
        url = read_redis_url()
        if args.check:
            _, _, _, chunks, _ = read_local_data(args.source)
            print(f"Redis 保存依赖、本地配置、{len(chunks)} 个知识块与索引检查通过；未验证 Redis 或云 API。")
            return 0

        # 创建连接失败就报错，不会自动退回 InMemorySaver。
        with open_redis_graph(url) as graph:
            if args.check_redis:
                print("Redis 连接与 checkpoint 索引初始化通过；未调用模型。")
                return 0
            if args.history:
                show_history(graph, session_id)
                return 0
            chat_config, embedding_config, rerank_config, chunks, index = read_local_data(args.source)
            with httpx.Client(follow_redirects=False) as client:
                services = Services(
                    chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                    embedding_model=OpenAIEmbeddings(
                        **embedding_config, check_embedding_ctx_length=False, chunk_size=10,
                        model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client,
                    ),
                    chat_model=ChatOpenAI(
                        model=chat_config["CHAT_MODEL"], base_url=chat_config["CHAT_BASE_URL"],
                        api_key=chat_config["CHAT_API_KEY"], temperature=0, max_tokens=900,
                        timeout=60, max_retries=0, http_client=client,
                    ),
                )
                print("本节使用 Redis 保存状态。退出后，再用相同会话编号可以接着聊。")
                print("命令：/session 编号 切换会话；/history 查看记录；/quit 退出。")
                pending, exit_code = iter(args.questions), 0
                while True:
                    try:
                        text = next(pending) if args.questions else input(f"\n[{session_id}] 你：")
                    except (StopIteration, EOFError, KeyboardInterrupt):
                        break
                    text = text.strip()
                    if not text:
                        continue
                    if text == "/quit":
                        break
                    try:
                        # 两个查看命令也会读 Redis，需要处理连接中断。
                        if text == "/history":
                            show_history(graph, session_id)
                            continue
                        if text == "/session" or text.startswith("/session "):
                            new_id = text.partition(" ")[2].strip()
                            if not 0 < len(new_id) <= 64:
                                print("用法：/session study；编号应为 1～64 字符。")
                            else:
                                show_history(graph, new_id)
                                session_id = new_id
                            continue
                        if args.questions:
                            print(f"\n[{session_id}] 你：{text}")
                        result = invoke_turn(graph, text, session_id, services, args.min_score)
                    except Exception as exc:
                        report_error(exc)
                        print("本次操作停止。恢复连接后可用 /history 核对已保存记录，或继续输入新问题。")
                        exit_code = 1
                        continue
                    # 只显示本次成功返回的结果，绝不从旧检查点拿答案来补。
                    print("\n回答：\n" + result["answer_text"])
                    if result["selected"]:
                        sources = [(row["rerank_score"], row["chunk"]) for row in result["selected"]]
                        show_sources(sources, show_context=args.show_context)
            return exit_code
    except Exception as exc:
        report_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
