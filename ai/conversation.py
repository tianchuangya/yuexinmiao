"""对话管理 —— JSON 文件存储历史对话"""

import os
import json
import uuid
from datetime import datetime


CONVERSATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "conversations"
)


class Conversation:
    """单次对话管理"""

    def __init__(self, conv_id: str = None, directory: str = None):
        self.directory = directory or CONVERSATIONS_DIR
        self.id = conv_id or self._generate_id()
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.messages = []

        # 确保目录存在
        os.makedirs(self.directory, exist_ok=True)

    @staticmethod
    def _generate_id() -> str:
        """生成唯一对话ID"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:6]
        return f"conv_{ts}_{short_uuid}"

    def add_message(self, role: str, content: str):
        """添加一条消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()

    def get_title(self, max_len: int = 30) -> str:
        """从首条用户消息生成对话标题"""
        for msg in self.messages:
            if msg["role"] == "user":
                text = msg["content"].replace("\n", " ").strip()
                if len(text) > max_len:
                    text = text[:max_len] + "..."
                return text
        return "新对话"

    def get_messages_for_api(self, skill_context: str = "") -> list:
        """获取适用于 API 调用的消息列表，前置 system message"""
        result = []
        if skill_context:
            result.append({"role": "system", "content": skill_context})
        for msg in self.messages:
            result.append({"role": msg["role"], "content": msg["content"]})
        return result

    def get_user_messages(self) -> list:
        """获取所有用户消息"""
        return [m for m in self.messages if m["role"] == "user"]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
        }

    def save(self) -> str:
        """保存到 JSON 文件，返回文件路径"""
        filepath = os.path.join(self.directory, f"{self.id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return filepath

    @staticmethod
    def load(conv_id: str, directory: str = None) -> "Conversation":
        """从 JSON 文件加载对话"""
        directory = directory or CONVERSATIONS_DIR
        filepath = os.path.join(directory, f"{conv_id}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"对话文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        conv = Conversation(conv_id=data["id"], directory=directory)
        conv.created_at = data.get("created_at", conv.created_at)
        conv.updated_at = data.get("updated_at", conv.updated_at)
        conv.messages = data.get("messages", [])
        return conv

    @staticmethod
    def delete(conv_id: str, directory: str = None) -> bool:
        """删除指定对话的 JSON 文件，返回是否成功"""
        import os as _os
        directory = directory or CONVERSATIONS_DIR
        filepath = _os.path.join(directory, f"{conv_id}.json")
        if _os.path.exists(filepath):
            _os.remove(filepath)
            return True
        # 也尝试在子文件夹中查找
        if _os.path.exists(directory):
            for root, dirs, files in _os.walk(directory):
                for f in files:
                    if f == f"{conv_id}.json":
                        _os.remove(_os.path.join(root, f))
                        return True
        return False

    @staticmethod
    def list_all(directory: str = None) -> list:
        """列出所有对话文件的信息（含标题）"""
        directory = directory or CONVERSATIONS_DIR
        if not os.path.exists(directory):
            return []
        result = []
        for filename in os.listdir(directory):
            if filename.endswith(".json"):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    msgs = data.get("messages", [])
                    # 生成标题
                    title = "新对话"
                    for m in msgs:
                        if m["role"] == "user":
                            t = m["content"].replace("\n", " ").strip()
                            title = t[:30] + ("..." if len(t) > 30 else "")
                            break
                    result.append({
                        "id": data.get("id", filename[:-5]),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(msgs),
                        "title": title,
                    })
                except Exception:
                    result.append({"id": filename[:-5], "created_at": "", "updated_at": "", "message_count": 0, "title": "（损坏）"})
        result.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        return result
