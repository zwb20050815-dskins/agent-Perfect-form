"""第八课 8.1：显式选择项目技能，复用 RAG、工具和 Redis 会话。"""

import argparse
import math
from pathlib import Path

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from lesson03b import DEFAULT_SOURCE, LessonError
from lesson05a import Services
from lesson06b import read_local_data, read_redis_url, report_error
from lesson07b import build_graph, open_redis_graph, show_result
from lesson08a_skills import SkillChatModel, list_skills, load_skill, valid_name

SESSION_PREFIX = "knowledge-agent:lesson08a:v1:"
EXAMPLE = "根据笔记解释贴现是什么，再计算票面金额10000元、年贴现率3%、剩余90天的贴现利息，按一年360天计算。"


def session_config(session_id, skill_name):
    # 对照实验分开记忆，避免启用/关闭技能两边的旧回答互相影响。
    return {"configurable": {"thread_id": f"{SESSION_PREFIX}{skill_name}:{session_id}"}}


def invoke_turn(graph, question, session_id, skill_name, services, min_score=0.5):
    inputs = {"user_question": question.strip(), "question": "", "answer_text": "",
              "min_score": min_score, "sources": [], "used_tools": []}
    return graph.invoke(inputs, config=session_config(session_id, skill_name), context=services, durability="sync")


def show_history(graph, session_id, skill_name):
    history = graph.get_state(session_config(session_id, skill_name)).values.get("history", [])
    print(f"技能 {skill_name} / 会话 {session_id}：最近 {len(history)} 轮已完成的问答。")
    for number, turn in enumerate(history, 1):
        print(f"{number}. 你：{turn['user_question']}\n   助手：{turn['answer']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="单次提问；不填则使用贴现示例")
    parser.add_argument("--skill", default="bank-study", help="技能目录名；none 表示本轮不加载技能")
    parser.add_argument("--session", default="study")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("--show-context", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-skills", action="store_true", help="列出技能名称和描述，不联网")
    mode.add_argument("--show-skill", action="store_true", help="查看选中的技能正文，不联网")
    mode.add_argument("--check", action="store_true", help="检查技能、本地模型配置、索引和图，不联网")
    mode.add_argument("--check-redis", action="store_true", help="检查 Redis 连接，不调用模型")
    mode.add_argument("--history", action="store_true", help="查看本技能与会话下的历史，不调用模型")
    mode.add_argument("--graph", action="store_true", help="显示沿用的7.2外层图，不联网")
    args = parser.parse_args()
    session_id = args.session.strip()
    if not valid_name(args.skill) or not 0 < len(session_id) <= 64:
        parser.error("技能名为小写字母、数字和单个连字符；会话编号为1～64字符。")
    if args.question is not None and not 0 < len(args.question.strip()) <= 1000:
        parser.error("问题为1～1000字符。")
    if not math.isfinite(args.min_score):
        parser.error("--min-score 必须是有限数字。")
    if args.question and any((args.list_skills, args.show_skill, args.check, args.check_redis, args.history, args.graph)):
        parser.error("查看或检查模式下不要同时传入问题。")
    try:
        if args.list_skills:
            for skill in list_skills():
                print(f"{skill.name}：{skill.description}")
            return 0
        if args.graph:
            print(build_graph().get_graph().draw_mermaid())
            return 0
        if args.check_redis or args.history:
            with open_redis_graph(read_redis_url()) as graph:
                if args.history:
                    show_history(graph, session_id, args.skill)
                else:
                    print("Redis 连接与 checkpoint 索引初始化通过；未调用模型。")
            return 0
        skill = load_skill(args.skill)
        if args.show_skill:
            print(f"{skill.name}\n{skill.description}\n\n{skill.body}" if skill else "none：本轮不加载技能。")
            return 0
        chat, embedding, rerank_config, chunks, index = read_local_data(args.source)
        url = read_redis_url()
        if args.check:
            build_graph()
            print(f"技能 {args.skill}、本地配置、图、{len(chunks)}个知识块和索引检查通过；未验证 Redis 或云 API。")
            return 0
        print(f"[skill] 已加载 {skill.name}；正文将交给工具调用模型。" if skill else "[skill] none：沿用7.2基础规则，不加载技能正文。")
        with open_redis_graph(url) as graph, httpx.Client(follow_redirects=False) as client:
            model = ChatOpenAI(model=chat["CHAT_MODEL"], base_url=chat["CHAT_BASE_URL"], api_key=chat["CHAT_API_KEY"],
                               temperature=0, max_tokens=1200, timeout=60, max_retries=0, http_client=client)
            services = Services(
                chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                embedding_model=OpenAIEmbeddings(**embedding, check_embedding_ctx_length=False, chunk_size=10,
                    model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client),
                chat_model=SkillChatModel(model, skill),
            )
            result = invoke_turn(graph, args.question or EXAMPLE, session_id, args.skill, services, args.min_score)
            show_result(result, args.show_context)
        return 0
    except Exception as exc:
        report_error(exc)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
