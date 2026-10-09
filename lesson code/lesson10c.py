"""第十课10.3：给个人知识Agent加一个独立的访问口令。"""

import argparse
import asyncio
from contextlib import asynccontextmanager
import hmac
import os
from pathlib import Path
import re
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lesson10a import check as check_agent, create_app as create_base_app
from lesson10a_runtime import error_types, open_runtime

ACCESS_FILE = Path(__file__).resolve().with_name(".env.access")
TOKEN_PATTERN = r"[A-Za-z0-9_-]{32,128}"


class AccessConfigError(Exception):
    pass


def read_token(path=ACCESS_FILE):
    """这个小文件只允许一行AGENT_ACCESS_TOKEN，不读取或修改千问密钥。"""
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024:
            raise AccessConfigError("请先运行 lesson10c.py --init-token，检查 .env.access 是否存在。")
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        raise AccessConfigError("无法读取 .env.access，请检查文件及读取权限。") from None
    match = re.fullmatch(r"AGENT_ACCESS_TOKEN=(" + TOKEN_PATTERN + r")(?:\r?\n)?", content)
    if not match:
        raise AccessConfigError(".env.access 格式不正确：应只保留 AGENT_ACCESS_TOKEN=口令 这一行。")
    return match.group(1)


def init_token(path=ACCESS_FILE):
    path = Path(path)
    if path.exists() or path.is_symlink():
        read_token(path)  # 有效的现有口令继续使用；无效文件不会自动覆盖。
        print("已有有效的访问口令，未修改文件。")
        return False
    token = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("AGENT_ACCESS_TOKEN=" + token + "\n")
    except OSError:
        raise AccessConfigError("未能新建 .env.access；已有文件不会被覆盖，请检查目录权限。") from None
    print("已生成 .env.access；口令保存在本机文件中，没有显示在终端。")
    print("用记事本打开文件，复制等号后面的值，在 /docs 的 Authorize 中使用。")
    return True


def create_app(runtime_factory=open_runtime, *, token_file=ACCESS_FILE):
    access = {}  # 只在服务运行期间保存口令，不放入State、Redis或响应。
    bearer = HTTPBearer(auto_error=False, scheme_name="AgentAccess",
                        description="填入 .env.access 中等号后面的访问口令；不要填写千问 API Key。")

    @asynccontextmanager
    async def protected_runtime():
        # 口令读取失败就不启动Agent；不会自动退回无鉴权模式。
        access["token"] = read_token(token_file)
        try:
            async with runtime_factory() as runtime:
                yield runtime
        finally:
            access.clear()

    async def require_access(request: Request,
            credential: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]):
        expected = access.get("token")
        if expected is None:
            raise HTTPException(status_code=503, detail="访问口令尚未加载，服务未就绪。")
        headers = request.headers.getlist("authorization")
        raw_header = headers[0] if len(headers) == 1 else ""
        valid = (len(headers) == 1 and credential is not None
                 and len(raw_header) <= 135
                 and re.fullmatch(r"(?i:Bearer) " + TOKEN_PATTERN, raw_header) is not None)
        if not valid or not hmac.compare_digest(credential.credentials, expected):
            raise HTTPException(status_code=401, detail="需要有效的 Agent 访问口令。",
                                headers={"WWW-Authenticate": "Bearer"})

    app = create_base_app(protected_runtime, protected_dependencies=[Depends(require_access)])
    app.title = "我的知识 Agent（访问口令）"
    app.version = "10.3"
    app.description = "先在 Authorize 填入个人访问口令，再提问或查看历史。session_id 是会话编号。"
    return app


app = create_app()  # 注册接口；导入模块时不读取口令、模型配置或连接Redis。


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--init-token", action="store_true", help="在本机新建访问口令，已有文件不覆盖")
    mode.add_argument("--check", action="store_true", help="检查口令配置，再检查知识索引、Redis和MCP；不调用云模型")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("端口为1～65535。")
    try:
        if args.init_token:
            init_token()
            return 0
        read_token()  # 启动前先给出清晰的口令配置提示。
        if args.check:
            asyncio.run(check_agent())
            print("访问口令格式检查通过；未显示口令。")
            return 0
    except AccessConfigError as exc:
        print(f"未完成：{exc}")
        return 1
    except Exception as exc:
        print(f"检查未完成（{error_types(exc)}）；请检查课程文件、Redis或MCP。")
        return 1
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
