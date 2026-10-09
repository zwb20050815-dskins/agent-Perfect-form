"""第九课9.3：本地查笔记 + MCP计算器，共用一个异步工具循环。"""

import json
import warnings

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from lesson03b import LessonError
from lesson07b_tools import SYSTEM_PROMPT, collect_answer, lookup_notes, make_tools
from lesson08a_skills import add_skill
from lesson09a import TOOL_NAME

MAX_MODEL_CALLS = 4


class ToolState(MessagesState):
    model_calls: int


def make_agent_tools(services, min_score=0.5, lookup=lookup_notes):
    # 只取7.2的检索工具；计算器只使用9.2的MCP代理，避免同名工具重复。
    search = next(item for item in make_tools(services, min_score, lookup) if item.name == "search_notes")
    remote = services.mcp_tools
    if len(remote) != 1 or remote[0].name != TOOL_NAME:
        raise LessonError("本轮需要一个已连接的MCP计算器。")
    return [search, *remote]


def build_tool_graph(bound_model, tools, skill=None):
    names = {item.name for item in tools}

    async def call_model(state: ToolState):
        count = state.get("model_calls", 0) + 1
        if count > MAX_MODEL_CALLS:
            raise LessonError("已达到本轮工具循环的模型调用上限。")
        print(f"[model] 工具循环第 {count} 次调用模型……", flush=True)
        messages = add_skill([SystemMessage(SYSTEM_PROMPT), *state["messages"]], skill)
        response = await bound_model.ainvoke(messages)
        if not isinstance(response, AIMessage) or response.invalid_tool_calls:
            raise LessonError("模型返回的工具请求不完整，未执行本次请求。")
        if response.response_metadata.get("finish_reason") in ("length", "content_filter"):
            raise LessonError("模型输出被截断或过滤，未执行本次请求。")
        if response.tool_calls:
            if count == MAX_MODEL_CALLS or len(response.tool_calls) > 3:
                raise LessonError("工具请求达到本轮上限，未执行本次请求。")
            ids = [call.get("id") for call in response.tool_calls]
            old_ids = {call["id"] for msg in state["messages"] if isinstance(msg, AIMessage)
                       for call in msg.tool_calls}
            if not all(ids) or len(ids) != len(set(ids)) or old_ids.intersection(ids):
                raise LessonError("工具请求缺少唯一编号，未执行本次请求。")
            if any(call["name"] not in names for call in response.tool_calls):
                raise LessonError("模型请求了本轮未提供的工具，未执行本次请求。")
            for call in response.tool_calls:
                print(f"    tool_calls：{call['name']} {json.dumps(call['args'], ensure_ascii=False)}", flush=True)
        elif not response.text.strip():
            raise LessonError("模型没有返回工具请求或有效回答。")
        return {"messages": [response], "model_calls": count}

    executor = ToolNode(tools, handle_tool_errors=False)

    async def execute_tools(state: ToolState, config: RunnableConfig):
        # ToolNode异步执行MCP代理；同步的search_notes由框架放到工作线程执行。
        print("[tools] ToolNode执行本轮请求……", flush=True)
        # 逐个等待工具完成；一项失败时，避免另一项仍在使用即将关闭的连接。
        result = {"messages": []}
        for call in state["messages"][-1].tool_calls:
            one = await executor.ainvoke([call], config=config)
            result["messages"].extend(one["messages"])
        for message in result["messages"]:
            print(f"[ToolMessage] {message.name}；对应请求ID：{message.tool_call_id}", flush=True)
            if message.name == "search_notes" and message.artifact:
                print(f"    本轮返回 {len(message.artifact['sources'])} 块通过筛选的笔记", flush=True)
        return result

    builder = StateGraph(ToolState)
    builder.add_node("model", call_model)
    builder.add_node("tools", execute_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "model")
    # 临时工具消息只属于本轮；Redis由外层图负责。
    return builder.compile(checkpointer=False)


async def run_agent(question, services, min_score=0.5, skill=None, lookup=lookup_notes):
    tools = make_agent_tools(services, min_score, lookup)
    graph = build_tool_graph(services.chat_model.bind_tools(tools), tools, skill)
    # 沿用7.2的处理：无保存器子图不继承外层的sync保存模式。
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"`durability` has no effect when no checkpointer is present\.",
                                category=UserWarning, module=r"langgraph\.pregel\.main")
        result = await graph.ainvoke({"messages": [HumanMessage(question)], "model_calls": 0},
                                    config={"recursion_limit": 16}, durability="exit")
    # 沿用原来的来源编号核对；引用失败时不进入remember。
    return collect_answer(result)
