"""第十课10.1：本机FastAPI问答接口；启动后打开 http://127.0.0.1:8000/docs。"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from redis.exceptions import RedisError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from lesson09b_mcp import open_mcp_tools
from lesson09c_tools import make_agent_tools
from lesson10a_runtime import BusyError, ClosingError, error_types, logger, open_runtime

SessionId = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1,
                                            max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
Question = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=1000)]


class ChatRequest(BaseModel):
    session_id: SessionId = Field(description="会话编号：1～64个英文字母、数字、下划线或连字符")
    question: Question = Field(description="本轮问题：1～1000字符")
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "session_id": "api-study",
        "question": "根据笔记解释贴现是什么，再计算票面金额10000元、年贴现率3%、剩余90天的贴现利息，按一年360天计算。",
    }})


class Source(BaseModel):
    id: str
    file: str
    heading: str
    text: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[Source]
    used_tools: list[str]
    selected_skill: str


class HistoryTurn(BaseModel):
    question: str
    answer: str


class HistoryResponse(BaseModel):
    session_id: str
    history: list[HistoryTurn]


class HealthResponse(BaseModel):
    status: str
    redis: str
    chunks: int
    busy: bool


def contains_redis_error(exc):
    if isinstance(exc, BaseExceptionGroup):
        return any(contains_redis_error(child) for child in exc.exceptions)
    return isinstance(exc, RedisError)


def create_app(runtime_factory=open_runtime, *, protected_dependencies=()):
    @asynccontextmanager
    async def lifespan(app):
        try:
            async with runtime_factory() as runtime:
                app.state.runtime = runtime
                yield
        except Exception as exc:
            logger.error("API启动或关闭失败（%s）。", error_types(exc))
            # 不让服务商原始异常、Redis URL等通过启动traceback泄露。
            raise RuntimeError("API未能正常启动或关闭，请检查本地配置与Redis。") from None
        finally:
            app.state.runtime = None

    app = FastAPI(title="我的知识 Agent", version="10.1", lifespan=lifespan,
                  description="本机学习接口：POST发送问题，GET查看状态或历史。", redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    def current_runtime(request):
        runtime = getattr(request.app.state, "runtime", None)
        if runtime is None:
            raise ClosingError()
        return runtime

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # 默认422会回显input；本课只返回字段规则，避免把误填的密钥再次输出。
        return JSONResponse(status_code=422, content={"detail":
            "输入格式不正确：session_id使用1～64个英文字母、数字、_或-；question使用1～1000字符；不要添加其他字段。"})

    @app.exception_handler(BusyError)
    async def busy_error(request, exc):
        return JSONResponse(status_code=409, content={"detail": "当前正在处理一个问题，请等它完成后再提问。"})

    @app.exception_handler(ClosingError)
    async def closing_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": "服务尚未就绪或正在关闭。"})

    async def execute(request, method, *args):
        try:
            return await getattr(current_runtime(request), method)(*args)
        except (BusyError, ClosingError):
            raise  # 交给上面对应的HTTP错误处理器。
        except Exception as exc:
            logger.error("接口操作失败（%s）。", error_types(exc))
            # 转成已处理的HTTP错误，避免ASGI服务器再次打印提供商原始异常。
            raise HTTPException(status_code=503 if contains_redis_error(exc) else 502,
                detail="本轮未能正常返回，请先查看会话历史，再决定是否重试；服务端日志仅记录异常类别。") from None

    @app.get("/health", response_model=HealthResponse, summary="检查服务与Redis")
    async def health(request: Request):
        """不调用Qwen或MCP；ok不表示云端密钥、余额或模型权限已经验证。"""
        return await execute(request, "health")

    @app.post("/chat", response_model=ChatResponse, summary="向知识Agent提问", dependencies=list(protected_dependencies), responses={
        409: {"description": "已有问题正在处理"}, 502: {"description": "问答未能正常返回"},
        503: {"description": "服务或Redis不可用"}})
    async def chat(payload: ChatRequest, request: Request):
        return await execute(request, "chat", payload.session_id, payload.question)

    @app.get("/sessions/{session_id}/history", response_model=HistoryResponse,
             summary="查看最近三轮已完成的问答", dependencies=list(protected_dependencies))
    async def history(session_id: SessionId, request: Request):
        return await execute(request, "history", session_id)

    return app


app = create_app()  # 此时只注册接口，尚未读取.env或连接Redis/MCP。


async def check():
    async with open_runtime() as runtime:
        health = await runtime.health()
        async with open_mcp_tools() as tools:
            make_agent_tools(replace(runtime.services, mcp_tools=tuple(tools)))
        print(f"检查通过：API依赖、配置、{health['chunks']}个知识块与索引、Redis、MCP。未调用云模型或执行计算。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="检查配置、索引、Redis和MCP；不启动HTTP服务或调用云模型")
    parser.add_argument("--port", type=int, default=8000, help="本机HTTP端口，默认8000")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("端口为1～65535。")
    if args.check:
        try:
            asyncio.run(check())
            return 0
        except Exception as exc:
            print(f"检查未通过（{error_types(exc)}）；请检查配置、课程文件、Redis及MCP。")
            return 1
    import uvicorn
    # 本节仅在本机、单进程运行；不使用reload，兼容Windows的MCP子进程。
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
