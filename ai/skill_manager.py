"""Skill 管理器 —— 对话总结与知识积累"""

import os
from .conversation import Conversation
from utils.paths import get_skill_file, get_skill_dir


SKILL_DIR = get_skill_dir()
SKILL_FILE = get_skill_file()

INITIAL_SKILL_CONTENT = """# 月星猫 Skill

> 这是月星猫桌宠的 AI 技能上下文。每次对话后会自动更新，融合新知识。

## 对话总结

（暂无历史对话记录）
"""


class SkillManager:
    """Skill（技能上下文）管理器

    每次对话结束后，将对话内容与现有 Skill 融合精简，
    使 Skill 始终保持紧凑且包含关键信息。
    """

    def __init__(self, skill_path: str = None):
        self.skill_path = skill_path or SKILL_FILE
        self._ensure_skill_file()

    def _ensure_skill_file(self):
        """确保 skill 文件和目录存在"""
        os.makedirs(os.path.dirname(self.skill_path), exist_ok=True)
        if not os.path.exists(self.skill_path):
            with open(self.skill_path, "w", encoding="utf-8") as f:
                f.write(INITIAL_SKILL_CONTENT)

    def get_context(self) -> str:
        """读取 skill 全文作为 AI 上下文"""
        self._ensure_skill_file()
        try:
            with open(self.skill_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            return content if content else ""
        except Exception:
            return ""

    def summarize_and_append(self, conversation: Conversation):
        """总结对话并融合到 skill 中

        策略：用 AI 生成精简总结，保持 skill 在合理大小。
        如果没有 AI 可用，则用简单的规则总结。
        """
        if not conversation.messages:
            return

        # 生成简单的规则总结（不需要 AI）
        summary = self._simple_summary(conversation)
        self._merge_into_skill(summary)

    def _simple_summary(self, conversation: Conversation) -> str:
        """简单的规则总结（不依赖 AI）"""
        user_msgs = [m for m in conversation.messages if m["role"] == "user"]
        assistant_msgs = [m for m in conversation.messages if m["role"] == "assistant"]

        lines = []
        lines.append(f"\n### {conversation.created_at[:10]} 对话")
        lines.append(f"- 消息数：{len(conversation.messages)}")
        lines.append(f"- 用户提问：{len(user_msgs)} 条")
        lines.append(f"- AI 回复：{len(assistant_msgs)} 条")

        # 提取用户问题关键词
        for msg in user_msgs[-3:]:  # 最近3条
            content = msg["content"][:100]
            lines.append(f"  - Q: {content}")

        return "\n".join(lines)

    def _merge_into_skill(self, summary: str):
        """将总结融合到 skill 文件中"""
        current = self.get_context()

        # 如果 skill 已经很长（超过3000字），裁剪旧内容
        if len(current) > 3000:
            # 保留前1500字 + 新总结
            current = current[:1500] + "\n\n...（旧内容已精简）..."

        new_content = current + "\n" + summary

        with open(self.skill_path, "w", encoding="utf-8") as f:
            f.write(new_content.strip() + "\n")
