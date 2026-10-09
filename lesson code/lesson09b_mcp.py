"""第九课9.2：把MCP工具包装为LangGraph可执行的异步Tool。"""

from contextlib import asynccontextmanager
import json

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from lesson09a import LessonError, SERVER_PATH, TOOL_NAME, result_data, server_parameters


def make_proxy(session, remote):
    async def invoke_mcp(**arguments):
        # 这段代码在客户端；真正的计算仍发生在MCP服务端进程。
        print(f"[mcp.call_tool] {remote.name} {json.dumps(arguments, ensure_ascii=False)}", flush=True)
        response = await session.call_tool(remote.name, arguments)
        data = result_data(response)  # is_error=True时抛错，停止本轮，不当作正常结果。
        print("[mcp.result] " + json.dumps(data, ensure_ascii=False), flush=True)
        # content交给模型；artifact供程序检查，ToolNode负责关联tool_call_id。
        return json.dumps(data, ensure_ascii=False), data

    return StructuredTool.from_function(
        name=remote.name, description=remote.description or "按一年360天计算贴现利息",
        args_schema=remote.input_schema, coroutine=invoke_mcp,
        response_format="content_and_artifact",
    )


@asynccontextmanager
async def open_mcp_tools(server_path=SERVER_PATH):
    print("[connect] 启动并连接9.1的MCP服务……", flush=True)
    async with stdio_client(server_parameters(server_path)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=20.0) as session:
            info = await session.initialize()
            listing = await session.list_tools()
            matches = [item for item in listing.tools if item.name == TOOL_NAME]
            if len(matches) != 1:
                raise LessonError("MCP服务未提供本课需要的唯一计算工具。")
            remote = matches[0]
            if not isinstance(remote.input_schema, dict) or remote.input_schema.get("type") != "object":
                raise LessonError("MCP计算器没有提供有效的参数schema。")
            print(f"[list_tools] {info.server_info.name} 提供 {remote.name}", flush=True)
            # 整个图都必须在yield所在的上下文中执行，不能先关闭会话再用代理工具。
            yield [make_proxy(session, remote)]
    print("[close] MCP会话和本次服务子进程已关闭。", flush=True)
