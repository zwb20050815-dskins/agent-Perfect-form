"""第十课10.1：把9.3的Agent接到长期运行的本机API。"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
import logging

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from lesson06b import read_local_data, read_redis_url
from lesson08a_skills import SKILLS_DIR
from lesson08b_catalog import discover_skills
from lesson09b_mcp import open_mcp_tools
from lesson09c import DEFAULT_SOURCE, MCPServices, build_graph

SESSION_PREFIX = "knowledge-agent:lesson10a:v1:"
logger = logging.getLogger("knowledge_agent.api")


class BusyError(Exception):
    pass


class ClosingError(Exception):
    pass


def error_types(exc):
    """只记录异常类别；原始异常正文可能包含服务地址或凭据。"""
    if isinstance(exc, BaseExceptionGroup):
        return ",".join(error_types(child) for child in exc.exceptions)
    return type(exc).__name__


def session_config(session_id):
    # 与9.3分开；同一API内使用相同编号才共享历史。
    return {"configurable": {"thread_id": SESSION_PREFIX + session_id}}


class AgentRuntime:
    def __init__(self, graph, services, redis_client, mcp_factory=open_mcp_tools):
        self.graph, self.services, self.redis = graph, services, redis_client
        self.mcp_factory = mcp_factory
        self.turn_task = None
        self.closing = False

    @property
    def busy(self):
        return self.turn_task is not None and not self.turn_task.done()

    async def health(self):
        if self.closing:
            raise ClosingError()
        await self.redis.ping()
        return {"status": "ok", "redis": "ok", "chunks": len(self.services.chunks), "busy": self.busy}

    async def history(self, session_id):
        if self.closing:
            raise ClosingError()
        state = await self.graph.aget_state(session_config(session_id))
        return {"session_id": session_id, "history": [
            {"question": item["user_question"], "answer": item["answer"]}
            for item in state.values.get("history", [])
        ]}

    async def chat(self, session_id, question):
        if self.closing:
            raise ClosingError()
        if self.busy:
            raise BusyError()
        # 检查与创建之间没有await，同一事件循环中不会同时接下两轮。
        task = asyncio.create_task(self._answer(session_id, question))
        self.turn_task = task
        task.add_done_callback(self._log_failure)
        # 网页关闭时，在途任务仍完成保存/清理，避免线程继续使用已关闭的连接。
        return await asyncio.shield(task)

    @staticmethod
    def _log_failure(task):
        if not task.cancelled():
            exc = task.exception()
            if exc is not None:
                logger.error("问答未能正常返回（%s）；可检查会话历史。", error_types(exc))

    async def _answer(self, session_id, question):
        # 同一个任务负责MCP进入、调用与退出；每轮得到一套新的代理工具。
        async with self.mcp_factory() as tools:
            services = replace(self.services, mcp_tools=tuple(tools))
            inputs = {"user_question": question, "question": "", "answer_text": "", "min_score": 0.5,
                      "sources": [], "used_tools": [], "selected_skill": ""}
            result = await self.graph.ainvoke(inputs, config=session_config(session_id),
                                             context=services, durability="sync")
        # 明确挑选响应字段，不直接返回整个State或运行时对象。
        return {"session_id": session_id, "answer": result["answer_text"], "sources": result["sources"],
                "used_tools": result["used_tools"], "selected_skill": result["selected_skill"]}

    async def close(self):
        self.closing = True
        if self.turn_task is not None:
            try:
                await asyncio.shield(self.turn_task)
            except Exception:
                pass  # 已由任务回调记录类别；仍继续关闭资源。


@asynccontextmanager
async def open_runtime():
    # 只在API启动时读配置、笔记和已有向量；这里不调用云模型、不重建向量。
    chat, embedding, rerank_config, chunks, index = read_local_data(DEFAULT_SOURCE)
    catalog = discover_skills(SKILLS_DIR)
    async with Redis.from_url(read_redis_url(), decode_responses=False, socket_connect_timeout=5, socket_timeout=5,
                              retry=Retry(NoBackoff(), 0), retry_on_timeout=False) as redis_client:
        await redis_client.ping()
        async with AsyncRedisSaver.from_conn_string(redis_client=redis_client) as saver:
            with httpx.Client(follow_redirects=False) as client:
                async with httpx.AsyncClient(follow_redirects=False) as async_client:
                    services = MCPServices(
                        chunks=chunks, index=index, client=client, rerank_config=rerank_config,
                        embedding_model=OpenAIEmbeddings(**embedding, check_embedding_ctx_length=False, chunk_size=10,
                            model_kwargs={"encoding_format": "float"}, max_retries=0, request_timeout=60, http_client=client),
                        chat_model=ChatOpenAI(model=chat["CHAT_MODEL"], base_url=chat["CHAT_BASE_URL"], api_key=chat["CHAT_API_KEY"],
                            temperature=0, max_tokens=1200, timeout=60, max_retries=0,
                            http_client=client, http_async_client=async_client),
                        catalog=catalog, skills_root=SKILLS_DIR,
                    )
                    runtime = AgentRuntime(build_graph(checkpointer=saver), services, redis_client)
                    try:
                        yield runtime
                    finally:
                        # 先等已接下的问答收尾，再退出外层HTTP/Redis上下文。
                        await runtime.close()
