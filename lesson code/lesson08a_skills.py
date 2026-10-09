"""第八课 8.1：读取项目内 SKILL.md，并把技能说明交给工具调用模型。"""

from dataclasses import dataclass
from pathlib import Path
import re

from langchain_core.messages import SystemMessage
import yaml

from lesson03b import LessonError

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
NAME_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str


def valid_name(name):
    return isinstance(name, str) and len(name) <= 64 and re.fullmatch(NAME_PATTERN, name) is not None


def load_skill(name, root=SKILLS_DIR):
    if name == "none":
        return None
    if not valid_name(name):
        raise LessonError("技能名称只能使用小写字母、数字和单个连字符，最多64字符。")
    root = Path(root).resolve()
    path = (root / name / "SKILL.md").resolve()
    if not path.is_relative_to(root):
        raise LessonError("技能文件必须位于项目的 skills 目录内。")
    if not path.is_file():
        raise LessonError(f"找不到技能 {name}，请用 --list-skills 查看名称。")
    if path.stat().st_size > 32_000:
        raise LessonError("本课每份 SKILL.md 最多32000字节，请精简说明。")
    try:
        text = path.read_text(encoding="utf-8-sig")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)(.*)\Z", text, re.DOTALL)
        if not match:
            raise LessonError("SKILL.md 顶部需要由两行 --- 包围的 name 和 description。")
        metadata = yaml.safe_load(match.group(1))
    except (UnicodeError, yaml.YAMLError):
        raise LessonError("SKILL.md 的编码或 YAML 格式不正确，请使用 UTF-8。") from None
    if not isinstance(metadata, dict) or metadata.get("name") != name:
        raise LessonError("SKILL.md 的 name 必须与所在文件夹名称一致。")
    description, body = metadata.get("description"), match.group(2).strip()
    if not isinstance(description, str) or not 0 < len(description.strip()) <= 1024 or not body:
        raise LessonError("技能需要简短的 description，以及非空的 Markdown 正文。")
    return Skill(name=name, description=description.strip(), body=body)


def list_skills(root=SKILLS_DIR):
    root = Path(root)
    if not root.is_dir():
        raise LessonError("找不到 skills 目录，请先安装本课文件。")
    # 本课列出摘要供人选择；只有选中的正文才会加入模型请求。
    return [load_skill(path.parent.name, root) for path in sorted(root.glob("*/SKILL.md"))
            if path.parent.name != "none"]


def add_skill(messages, skill):
    if skill is None:
        return messages
    if not messages or not isinstance(messages[0], SystemMessage) or not isinstance(messages[0].content, str):
        raise LessonError("工具循环缺少基础 system 消息，无法加载技能。")
    addition = (f"\n\n本轮启用项目技能：{skill.name}\n适用范围：{skill.description}\n"
                "以下为项目维护者提供的工作方法。保留已有工具规则和本轮用户要求，只应用适合当前任务的部分。\n"
                + skill.body)
    # 创建新消息，避免修改上一课的基础提示或其他会话的消息。
    first = messages[0].model_copy(update={"content": messages[0].content + addition})
    return [first, *messages[1:]]


class SkillBoundModel:
    def __init__(self, bound_model, skill):
        self.bound_model, self.skill = bound_model, skill

    def invoke(self, messages):
        return self.bound_model.invoke(add_skill(messages, self.skill))


class SkillChatModel:
    """给7.2的聊天模型加一层：历史补全照旧，工具循环读取技能说明。"""

    def __init__(self, model, skill):
        self.model, self.skill = model, skill

    def invoke(self, messages):
        # prepare 只负责补全当前问题，不把技能要求混进用户的问题。
        return self.model.invoke(messages)

    def bind_tools(self, tools):
        return SkillBoundModel(self.model.bind_tools(tools), self.skill)
