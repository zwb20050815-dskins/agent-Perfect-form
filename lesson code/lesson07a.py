"""第七课 7.1：模型提出工具调用，Python 执行，再由模型回答。"""

import argparse
from decimal import Decimal, ROUND_HALF_UP
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from lesson01 import read_config

MAX_MODEL_CALLS = 3
DEMO_QUESTION = "票面金额 10000 元，年贴现率 3%，剩余 90 天，按一年 360 天计算贴现利息。"
SYSTEM_PROMPT = """你是中文工具调用学习助手。本节提供按一年 360 天计算贴现利息的工具。
用户要求计算具体贴现利息且参数完整时，调用工具，以工具返回的结果为计算依据，不自行编造结果。
annual_rate_percent 使用百分数，例如 3 表示 3%，不是 0.03。
缺少票面金额、年贴现率或剩余天数时，先询问缺失的参数；不要猜测。
本工具只支持一年 360 天的教学公式，回答时说明这一假设；用户要求其他规则时说明不支持。
普通问候或介绍能力时直接简短回答，不需要工具。
工具报错时说明失败；可以在用户原始信息明确支持的情况下修正参数，不能随意改成其他数值。
你没有在本节读取用户的笔记或 Redis 历史，也没有调用算命 API。"""


class LessonError(Exception):
    pass


class DiscountInput(BaseModel):
    face_value: float = Field(strict=True, gt=0, le=1_000_000_000_000, description="票面金额，单位：元")
    annual_rate_percent: float = Field(strict=True, ge=0, le=100, description="年贴现率的百分数；3 表示 3%")
    days: int = Field(strict=True, ge=0, le=3660, description="剩余贴现天数，整数")


@tool(args_schema=DiscountInput)
def calculate_discount_interest(face_value: float, annual_rate_percent: float, days: int) -> dict:
    """按一年 360 天计算贴现利息：票面金额 × 年贴现率百分数 ÷ 100 × 天数 ÷ 360。"""
    # Decimal 避免用二进制浮点数直接处理金额；结果四舍五入到分。
    interest = Decimal(str(face_value)) * Decimal(str(annual_rate_percent)) / 100 * days / 360
    return {
        "interest_yuan": str(interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "face_value": face_value, "annual_rate_percent": annual_rate_percent,
        "days": days, "year_days": 360,
    }


TOOLS = [calculate_discount_interest]


class ToolState(MessagesState):
    # messages 沿用 MessagesState 的合并规则；model_calls 是普通字段，返回新值覆盖旧值。
    model_calls: int


def tool_error_message(exc: Exception) -> str:
    return f"工具执行失败（{type(exc).__name__}）。请检查金额、百分数年贴现率和整数天数的格式与范围。"


def build_graph(model):
    def call_model(state: ToolState) -> dict:
        count = state.get("model_calls", 0) + 1
        if count > MAX_MODEL_CALLS:
            raise LessonError("已达到本轮模型调用上限，请简化问题后重试。")
        print(f"[model] 第 {count} 次调用模型……", flush=True)
        response = model.invoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])
        if not isinstance(response, AIMessage) or response.invalid_tool_calls:
            raise LessonError("模型返回的工具调用格式不完整，未执行本次工具请求。")
        if response.response_metadata.get("finish_reason") in ("length", "content_filter"):
            raise LessonError("模型输出被截断或过滤，未执行本次工具请求。")
        if response.tool_calls:
            if count == MAX_MODEL_CALLS:
                raise LessonError("模型仍要求调用工具，已达到本轮上限；本次工具请求未执行。")
            if len(response.tool_calls) > 3:
                raise LessonError("一次最多执行 3 个工具请求，请减少计算任务。")
            ids = [call.get("id") for call in response.tool_calls]
            if not all(ids) or len(ids) != len(set(ids)):
                raise LessonError("工具请求缺少有效的唯一编号，未执行本次工具请求。")
            for call in response.tool_calls:
                print(f"    模型请求：{call['name']} {json.dumps(call['args'], ensure_ascii=False)}", flush=True)
        elif not response.text.strip():
            raise LessonError("模型没有返回回答或工具请求，请检查模型是否支持工具调用。")
        else:
            print("    模型给出回答，没有新的工具请求。", flush=True)
        # 只返回本次新消息；messages 的合并规则会把它接到之前的消息后面。
        return {"messages": [response], "model_calls": count}

    executor = ToolNode(TOOLS, handle_tool_errors=tool_error_message)

    def execute_tools(state: ToolState, config: RunnableConfig) -> dict:
        print("[tools] Python 开始执行工具……", flush=True)
        result = executor.invoke(state, config=config)
        for message in result["messages"]:
            print(f"    工具结果（{message.name} / {message.status}）：{message.content}", flush=True)
        return result

    builder = StateGraph(ToolState)
    builder.add_node("model", call_model)
    builder.add_node("tools", execute_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "model")
    return builder.compile()


def run_question(graph, question: str) -> dict:
    result = graph.invoke({"messages": [HumanMessage(question)], "model_calls": 0},
                          config={"recursion_limit": 12})
    print("\n回答：\n" + result["messages"][-1].text)
    return result


class DemoModel:
    """固定的模拟模型：仅供观察流程；计算器和 LangGraph 仍然真实执行。"""

    def invoke(self, messages):
        if isinstance(messages[-1], ToolMessage):
            data = json.loads(messages[-1].content)
            return AIMessage(content=f"【模拟回答】按一年 360 天计算，贴现利息为 {data['interest_yuan']} 元。")
        return AIMessage(content="", tool_calls=[{
            "name": "calculate_discount_interest", "id": "demo-call-1", "type": "tool_call",
            "args": {"face_value": 10000, "annual_rate_percent": 3, "days": 90},
        }])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="单次提问；省略时使用贴现利息示例")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="运行固定的离线演示，不调用模型")
    mode.add_argument("--check", action="store_true", help="检查本地模型配置、工具与图，不调用模型")
    mode.add_argument("--graph", action="store_true", help="输出图结构，不读取配置或调用模型")
    args = parser.parse_args()
    if args.question is not None and (not args.question.strip() or args.demo or args.check or args.graph):
        parser.error("问题不能为空；演示、检查或查看图时不要同时传入问题。")
    try:
        if args.demo:
            print("离线演示：模型的选择与回答是模拟的；Python 工具和 LangGraph 实际运行。")
            print("问题：" + DEMO_QUESTION)
            run_question(build_graph(DemoModel()), DEMO_QUESTION)
            return 0
        if args.graph:
            print(build_graph(DemoModel()).get_graph().draw_mermaid())
            return 0
        try:
            config = read_config()
        except ValueError as exc:
            raise LessonError(str(exc)) from None
        if args.check:
            build_graph(DemoModel())
            print("模型配置、工具与图的本地检查通过；尚未验证云 API 或模型的工具调用能力。")
            return 0
        model = ChatOpenAI(
            model=config["CHAT_MODEL"], base_url=config["CHAT_BASE_URL"], api_key=config["CHAT_API_KEY"],
            temperature=0, max_tokens=900, timeout=60, max_retries=0,
        )
        # bind_tools 告诉模型有哪些工具和参数；真正执行由 ToolNode 负责。
        model_with_tools = model.bind_tools(TOOLS)
        run_question(build_graph(model_with_tools), args.question or DEMO_QUESTION)
        return 0
    except LessonError as exc:
        print(f"未完成：{exc}")
    except Exception as exc:
        # 原始接口报错可能包含地址或密钥，只输出异常类别。
        print(f"流程未完成（{type(exc).__name__}）；请检查网络、模型配置以及服务商是否支持工具调用。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
