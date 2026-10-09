"""第八课8.2：每轮自动选择技能，再按需读取正文并调用工具。"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, replace
import math
from pathlib import Path

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from lesson03b import DEFAULT_SOURCE, LessonError
from lesson05a import Services
from lesson06a import remember
from lesson06b import read_local_data, read_redis_url, report_error
from lesson07b import AgentState, prepare, show_result
from lesson07b_tools import lookup_notes, run_agent
from lesson08a import EXAMPLE
from lesson08a_skills import SKILLS_DIR, SkillChatModel, load_skill
from lesson08b_catalog import SkillSummary, choose_skill, discover_skills

SESSION_PREFIX = "knowledge-agent:lesson08b:v1:"


@dataclass
class AutoServices(Services):
    catalog: tuple[SkillSummary, ...] = ()
    skills_root: Path = SKILLS_DIR


class AutoState(AgentState, total=False):
    selected_skill: str


def select_skill(state: AutoState, runtime: Runtime[AutoServices]):
    services = runtime.context
    return {"selected_skill": choose_skill(state["question"], services.chat_model, services.catalog)}


def build_graph(checkpointer=None, lookup=lookup_notes):
    def agent(state: AutoState, runtime: Runtime[AutoServices]):
        services, name = runtime.context, state["selected_skill"]
        if name == "none":
            skill = None
            print("[skill] 不读取技能正文；基础工具仍然可用。", flush=True)
        else:
            summary = next((item for item in services.catalog if item.name == name), None)
            if summary is None:
                raise LessonError("选中的技能不在本轮目录中。")
            skill = load_skill(name, services.skills_root)
            if skill.description != summary.description:
                raise LessonError("技能描述在运行中发生改变，请重新运行以刷新目录。")
            print(f"[skill] 现在读取 {name} 正文，交给本轮工具调用模型。", flush=True)
        # 只包装本轮的模型，不修改共享Services，避免下轮残留旧技能。
        turn_services = replace(services, chat_model=SkillChatModel(services.chat_model, skill))
        return run_agent(state["question"], turn_services, state["min_score"], lookup)

    builder = StateGraph(AutoState, context_schema=AutoServices)
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
    # 同一会话可在不同轮次选不同技能，历史仍连贯。
    return {"configurable": {"thread_id": SESSION_PREFIX + session_id}}


@contextmanager
def open_redis_graph(url):
    with Redis.from_url(url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5,
                        retry=Retry(NoBackoff(), 0), retry_on_timeout=False) as client:
        client.ping()
        with RedisSaver.from_conn_string(redis_client=client) as saver:
            saver.setup()
            yield build_graph(checkpointer=saver)


def invoke_turn(graph, question, session_id, services, min_score=0.5):
    inputs = {"user_question": question.strip(), "question": "", "answer_text": "", "min_score": min_score,
              "sources": [], "used_tools": [], "selected_skill": ""}
    return graph.invoke(inputs, config=session_config(session_id), context=services, durability="sync")


def show_history(graph, session_id):
    history = graph.get_state(session_config(session_id)).values.get("history", [])
    print(f"会话 {session_id}：最近 {len(history)} 轮已完成的问答。")
    for number, turn in enumerate(history, 1):
        print(f"{number}. 你：{turn['user_question']}\n   助手：{turn['answer']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="单次提问；不填使用贴现解释与计算例题")
    parser.add_argument("--session", default="study")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--show-context", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-skills", action="store_true", help="只读取并列出技能元信息，不联网")
    mode.add_argument("--check", action="store_true", help="检查技能目录元信息、配置、索引和图，不联网")
    mode.add_argument("--check-redis", action="store_true", help="检查 Redis 连接，不调用模型")
    mode.add_argument("--history", action="store_true", help="查看本会话历史，不调用模型")
    mode.add_argument("--graph", action="store_true", help="显示含select_skill节点的图，不联网")
    args = parser.parse_args()
    session_id = args.session.strip()
    if not 0 < len(session_id) <= 64:
        parser.error("会话编号为1～64字符。")
    if args.question is not None and not 0 < len(args.question.strip()) <= 1000:
        parser.error("问题为1～1000字符。")
    if not math.isfinite(args.min_score):
        parser.error("--min-score 必须是有限数字。")
    if args.question and any((args.list_skills, args.check, args.check_redis, args.history, args.graph)):
        parser.error("查看或检查模式下不要同时传入问题。")
    try:
        if args.graph:
            print(build_graph().get_graph().draw_mermaid())
            return 0
        if args.check_redis or args.history:
            with open_redis_graph(read_redis_url()) as graph:
                if args.history:
                    show_history(graph, session_id)
                else:
                    print("Redis连接与checkpoint索引初始化通过；未调用模型。")
            return 0
        catalog = discover_skills(SKILLS_DIR)
        if args.list_skills:
            for item in catalog:
                print(f"{item.name}：{item.description}")
            return 0
        chat, embedding, rerank_config, chunks, index = read_local_data(args.source)
        url = read_redis_url()
        if args.check:
            build_graph()
            print(f"{len(catalog)}项技能元信息、配置、{len(chunks)}个知识块、索引与图检查通过。")
            print("尚未连接Redis或云API；技能正文在选中后才读取并校验。")
            return 0
        with open_redis_graph(url) as graph, httpx.Client(follow_redirects=False) as client:
            services = AutoServices(
                chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                embedding_model=OpenAIEmbeddings(**embedding, check_embedding_ctx_length=False, chunk_size=10,
                    model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client),
                chat_model=ChatOpenAI(model=chat["CHAT_MODEL"], base_url=chat["CHAT_BASE_URL"], api_key=chat["CHAT_API_KEY"],
                    temperature=0, max_tokens=1200, timeout=60, max_retries=0, http_client=client),
                catalog=catalog, skills_root=SKILLS_DIR,
            )
            result = invoke_turn(graph, args.question or EXAMPLE, session_id, services, args.min_score)
            show_result(result, args.show_context)
        return 0
    except Exception as exc:
        report_error(exc)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
