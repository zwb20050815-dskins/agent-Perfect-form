"""日常问答入口：使用全部已入库的HTML和PDF，复用第八课的Agent。"""

from pathlib import Path

from lesson08b import main


if __name__ == "__main__":
    raise SystemExit(main(
        default_source=Path(__file__).resolve().parent / "data/chunks/个人笔记.chunks.json",
        default_session="library",
        session_prefix="knowledge-agent:library:v1:",
        default_question="根据笔记，风险管理的三道防线分别是什么？",
    ))
