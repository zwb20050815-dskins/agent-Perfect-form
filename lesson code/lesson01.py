"""第一课：配置检查与单次 Qwen3 调用，尚未接入知识库。"""

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def read_config() -> dict[str, str]:
    # 从脚本所在文件夹加载，而不是依赖终端当前目录。
    load_dotenv(Path(__file__).with_name(".env"))
    names = ("CHAT_BASE_URL", "CHAT_MODEL", "CHAT_API_KEY")
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError("请在 .env 填写：" + "、".join(missing))
    try:
        parsed = urlsplit(values["CHAT_BASE_URL"])
        hostname = parsed.hostname
    except ValueError as exc:
        raise ValueError("CHAT_BASE_URL 格式不正确。") from exc
    if parsed.scheme != "https" or not hostname:
        raise ValueError("本课使用云 API，CHAT_BASE_URL 应为服务商的 HTTPS 基础地址。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("CHAT_BASE_URL 应为不含账号、密码、查询参数或片段的基础地址。")
    if parsed.path.rstrip("/").endswith("/chat/completions"):
        raise ValueError("请填写兼容 API 基础地址，不要加 /chat/completions。")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="用三句话解释 RAG 中的检索有什么用。")
    parser.add_argument("--check", action="store_true", help="仅检查本地配置，不请求云 API")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    try:
        config = read_config()
    except ValueError as exc:
        print(f"配置未完成：{exc}")
        return 2
    if args.check:
        print("本地配置检查通过；尚未验证网络、密钥、模型权限或余额。")
        return 0

    model = ChatOpenAI(
        model=config["CHAT_MODEL"],
        api_key=config["CHAT_API_KEY"],
        base_url=config["CHAT_BASE_URL"],
        timeout=60,
        max_retries=0,
    )
    try:
        answer = model.invoke([
            ("system", "你是一位中文编程学习助手。当前程序没有接入用户的笔记、检索或外部工具；不要声称已读取它们。"),
            ("human", args.question),
        ])
    except Exception as exc:
        # 不把包含请求地址、服务商错误正文或请求内容的原始异常打到终端。
        print(f"调用失败（{type(exc).__name__}）。请检查网络、地域、模型 ID、密钥及账户额度。")
        print("排查时提供异常类别即可，不要提供 API Key。")
        return 1
    print(answer.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
