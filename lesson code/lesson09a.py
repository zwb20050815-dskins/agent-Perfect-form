"""第九课9.1：启动本地 MCP 服务，发现并调用计算工具，不调用大模型。"""

import argparse
import asyncio
import json
import math
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

SERVER_PATH = Path(__file__).resolve().with_name("lesson09a_server.py")
TOOL_NAME = "calculate_discount_interest"


class LessonError(Exception):
    pass


def server_parameters(server_path=SERVER_PATH):
    path = Path(server_path).resolve()
    if not path.is_file():
        raise LessonError("找不到 lesson09a_server.py，请先安装本课文件。")
    # 使用当前uv环境的Python；参数分开传递，不拼接shell命令，支持中文和空格路径。
    return StdioServerParameters(command=sys.executable, args=["-u", str(path)],
                                 cwd=str(path.parent), env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})


def result_data(result):
    if not isinstance(result, types.CallToolResult):
        raise LessonError("MCP返回了本课不支持的结果类型。")
    if result.is_error:
        raise LessonError("服务端拒绝了本次计算。请核对金额、百分数年贴现率和整数天数的范围。")
    data = result.structured_content
    if not isinstance(data, dict) or not isinstance(data.get("interest_yuan"), str):
        raise LessonError("MCP没有返回完整的结构化计算结果。")
    return data


async def run_client(arguments, *, list_only=False, check_only=False, server_path=SERVER_PATH):
    print("[connect] 启动本机MCP服务子进程，使用stdio连接……", flush=True)
    async with stdio_client(server_parameters(server_path)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=20.0) as session:
            info = await session.initialize()  # 先握手，确认协议和服务能力。
            print(f"[initialize] 已连接：{info.server_info.name}；协议：{info.protocol_version}", flush=True)
            listing = await session.list_tools()  # 这里只查看工具，没有计算。
            matches = [tool for tool in listing.tools if tool.name == TOOL_NAME]
            if len(matches) != 1:
                raise LessonError("服务没有提供本课需要的唯一计算工具。")
            selected = matches[0]
            print(f"[list_tools] 发现工具：{selected.name}", flush=True)
            if list_only:
                print("用途：" + (selected.description or ""))
                print("参数schema：\n" + json.dumps(selected.input_schema, ensure_ascii=False, indent=2))
            elif not check_only:
                print("[call_tool] 发送参数：" + json.dumps(arguments, ensure_ascii=False), flush=True)
                result = await session.call_tool(TOOL_NAME, arguments)
                # SDK会按工具公布的output_schema校验成功结果；本课再检查错误标记及所需字段。
                data = result_data(result)
                print("[result] MCP服务端返回：\n" + json.dumps(data, ensure_ascii=False, indent=2))
                print(f"\n贴现利息：{data['interest_yuan']} 元（一年按{data['year_days']}天）。")
            else:
                print("MCP启动、握手与工具发现通过；没有执行计算，也没有调用模型。")
    # 离开两个async with后，SDK关闭会话、管道并等待/清理本次启动的子进程。
    print("[close] MCP会话和本次服务子进程已关闭。", flush=True)


def report_error(exc):
    # 异步上下文有时会把内部异常包成ExceptionGroup；只显示可理解的本地错误。
    pending = [exc]
    while pending:
        current = pending.pop()
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
        elif isinstance(current, LessonError):
            print(f"未完成：{current}")
            return
    print(f"MCP调用未完成（{type(exc).__name__}）；请确认已运行uv sync，并检查服务端文件及参数。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--face-value", type=float, default=10000)
    parser.add_argument("--annual-rate", type=float, default=3, help="百分数；3表示3%%")
    parser.add_argument("--days", type=int, default=90)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list-tools", action="store_true", help="启动服务、握手并列出工具，不执行计算")
    mode.add_argument("--check", action="store_true", help="实际检查MCP连接与工具发现，不执行计算或调用模型")
    args = parser.parse_args()
    if not math.isfinite(args.face_value) or not math.isfinite(args.annual_rate):
        parser.error("金额和年贴现率必须是有限数字。")
    arguments = {"face_value": args.face_value, "annual_rate_percent": args.annual_rate, "days": args.days}
    try:
        asyncio.run(run_client(arguments, list_only=args.list_tools, check_only=args.check))
        return 0
    except KeyboardInterrupt:
        print("已取消MCP演示。")
    except Exception as exc:
        report_error(exc)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
