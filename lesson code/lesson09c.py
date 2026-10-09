"""第九课9.3：查全部笔记、自动选Skill、MCP计算与Redis记忆。"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import math
from pathlib import Path

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from redis.asyncio import Redis
from redis.backoff import NoBackoff
from redis.asyncio.retry import Retry

from lesson03b import LessonError
from lesson06a import remember
from lesson06b import read_local_data, read_redis_url, report_error as report_base_error
from lesson07b import prepare, show_result
from lesson07b_tools import lookup_notes
from lesson08a_skills import SKILLS_DIR, load_skill
from lesson08b import AutoServices, AutoState, select_skill
from lesson08b_catalog import discover_skills
from lesson09a import LessonError as MCPError
from lesson09b_mcp import open_mcp_tools
from lesson09c_tools import make_agent_tools, run_agent

DEFAULT_SOURCE = Path(__file__).resolve().parent / "data/chunks/个人笔记.chunks.json"
SESSION_PREFIX = "knowledge-agent:lesson09c:v1:"
EXAMPLE = "根据笔记解释贴现是什么，再计算票面金额10000元、年贴现率3%、剩余90天的贴现利息，按一年360天计算。"


@dataclass
class MCPServices(AutoServices):
    mcp_tools: tuple = ()


def build_graph(checkpointer=None, lookup=lookup_notes):
    async def agent(state: AutoState, runtime: Runtime[MCPServices]):
        services, name = runtime.context, state["selected_skill"]
        skill = None
        if name == "none":
            print("[skill] 不读取技能正文；两个工具仍然可用。", flush=True)
        else:
            summary = next((item for item in services.catalog if item.name == name), None)
            if summary is None:
                raise LessonError("选中的技能不在本轮目录中。")
            skill = load_skill(name, services.skills_root)
            if skill.description != summary.description:
                raise LessonError("技能描述发生变化，请重新运行以刷新目录。")
            print(f"[skill] 读取 {name} 正文，只应用于本轮。", flush=True)
        return await run_agent(state["question"], services, state["min_score"], skill, lookup)

    builder = StateGraph(AutoState, context_schema=MCPServices)
    # 这三个旧节点保持同步写法；ainvoke会在线程中执行它们。
    builder.add_node("prepare", prepare)
    builder.add_node("select_skill", select_skill)
    builder.add_node("agent", agent)
    builder.add_node("remember", remember)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "select_skill")
    builder.add_edge("select_skill", "agent")
    builder.add_edge("agent", "remember")
    builder.add_edge("remember", END)
    return builder.compile(checkpointer=checkpointer)


def session_config(session_id):
    return {"configurable": {"thread_id": SESSION_PREFIX + session_id}}


@asynccontextmanager
async def open_redis_graph(url, lookup=lookup_notes):
    async with Redis.from_url(url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5,
                              retry=Retry(NoBackoff(), 0), retry_on_timeout=False) as client:
        await client.ping()
        # 此版本进入异步上下文时自动初始化checkpoint索引。
        async with AsyncRedisSaver.from_conn_string(redis_client=client) as saver:
            yield build_graph(checkpointer=saver, lookup=lookup)


async def invoke_turn(graph, question, session_id, services, min_score=0.5):
    inputs = {"user_question": question.strip(), "question": "", "answer_text": "", "min_score": min_score,
              "sources": [], "used_tools": [], "selected_skill": ""}
    # 不传history，按thread_id从Redis恢复；临时资料每轮清空。
    return await graph.ainvoke(inputs, config=session_config(session_id), context=services, durability="sync")


async def show_history(graph, session_id):
    snapshot = await graph.aget_state(session_config(session_id))
    history = snapshot.values.get("history", [])
    print(f"会话 {session_id}：最近 {len(history)} 轮已完成的问答。")
    for number, turn in enumerate(history, 1):
        print(f"{number}. 你：{turn['user_question']}\n   助手：{turn['answer']}")


async def run(args):
    if args.graph:
        print(build_graph().get_graph().draw_mermaid())
        return
    if args.history or args.check_redis:
        async with open_redis_graph(read_redis_url()) as graph:
            if args.history:
                await show_history(graph, args.session)
            else:
                print("Redis连接与checkpoint索引初始化通过；未调用模型或启动MCP。")
        return
    catalog = discover_skills(SKILLS_DIR)
    if args.list_skills:
        for item in catalog:
            print(f"{item.name}：{item.description}")
        return
    chat, embedding, rerank_config, chunks, index = read_local_data(args.source)
    async with open_redis_graph(read_redis_url()) as graph, open_mcp_tools() as mcp_tools:
        if args.check:
            services = MCPServices(chunks=chunks, index=index, embedding_model=None, rerank_config=rerank_config,
                                   client=None, chat_model=None, catalog=catalog, mcp_tools=tuple(mcp_tools))
            names = [item.name for item in make_agent_tools(services)]
            print(f"检查通过：{len(chunks)}个知识块与索引、{len(catalog)}项技能摘要、Redis、MCP和图。")
            print("工具：" + "、".join(names) + "；未调用云模型或执行计算。")
            return
        # 旧RAG/问题补全/技能选择使用同步客户端；工具循环使用异步聊天客户端。
        with httpx.Client(follow_redirects=False) as client:
            async with httpx.AsyncClient(follow_redirects=False) as async_client:
                services = MCPServices(
                    chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                    embedding_model=OpenAIEmbeddings(**embedding, check_embedding_ctx_length=False, chunk_size=10,
                        model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client),
                    chat_model=ChatOpenAI(model=chat["CHAT_MODEL"], base_url=chat["CHAT_BASE_URL"], api_key=chat["CHAT_API_KEY"],
                        temperature=0, max_tokens=1200, timeout=60, max_retries=0,
                        http_client=client, http_async_client=async_client),
                    catalog=catalog, skills_root=SKILLS_DIR, mcp_tools=tuple(mcp_tools),
                )
                result = await invoke_turn(graph, args.question or EXAMPLE, args.session, services, args.min_score)
    # Redis保存完成、MCP连接收尾后，再向用户展示本轮结果。
    show_result(result, args.show_context)


def report_error(exc):
    pending, leaves = [exc], []
    while pending:
        current = pending.pop()
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
        else:
            leaves.append(current)
    for leaf in leaves:
        if isinstance(leaf, (LessonError, MCPError)):
            print(f"未完成：{leaf}")
            return
    report_base_error(leaves[0] if leaves else exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="不填则运行解释贴现并计算90天利息的例题")
    parser.add_argument("--session", default="mcp-study", help="同一编号继续追问；本课独立于旧入口")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--show-context", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查配置/索引/技能摘要，并连接Redis与MCP；不调用云模型或计算")
    mode.add_argument("--check-redis", action="store_true", help="只连接Redis并初始化checkpoint索引")
    mode.add_argument("--history", action="store_true", help="从Redis读取当前会话最近三轮已完成的问答")
    mode.add_argument("--list-skills", action="store_true", help="只读取技能摘要")
    mode.add_argument("--graph", action="store_true", help="只显示流程，不读取配置或连接服务")
    args = parser.parse_args(argv)
    args.session = args.session.strip()
    if not 0 < len(args.session) <= 64:
        parser.error("会话编号为1～64字符。")
    if args.question is not None and (not 0 < len(args.question.strip()) <= 1000
            or any((args.check, args.check_redis, args.history, args.list_skills, args.graph))):
        parser.error("问题为1～1000字符；查看或检查模式下不要同时传入问题。")
    if not math.isfinite(args.min_score):
        parser.error("--min-score 必须是有限数字。")
    try:
        asyncio.run(run(args))
        return 0
    except KeyboardInterrupt:
        print("已取消本轮问答。")
    except Exception as exc:
        report_error(exc)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
