"""AI API 客户端 —— OpenAI 兼容接口封装（支持流式输出和工具调用）"""

import json
from .tools import TOOL_DEFINITIONS, execute_tool, PROJECT_ROOT

# 系统提示词（让 AI 知道自己可以操作文件）
SYSTEM_PROMPT = f"""你是月星猫桌宠的 AI 助手。你拥有强大的文件操作和代码能力，类似 Claude Code。

你可以通过工具来：
- 📖 读取文件 (read_file)
- ✏️ 创建/覆盖文件 (write_file)
- 🔧 精确编辑文件 (edit_file，old_string 必须唯一匹配)
- 📂 列出目录 (list_directory)
- 🔍 搜索代码/内容 (search_content，支持正则)
- 🗑️ 删除文件 (delete_file)
- 📦 移动/重命名文件 (move_file)
- 💻 执行命令 (execute_command)

规则：
1. 项目根目录: {PROJECT_ROOT}
2. 所有文件路径相对于项目根目录。
3. 使用 edit_file 前先用 read_file 确认内容。
4. 回复简洁有用，代码改动时解释原因。
5. 中文回复用户。
"""


class AIClient:
    """OpenAI 兼容 API 客户端（流式 + 工具调用）"""

    def __init__(self, ai_config: dict):
        self.model = ai_config.get("model", "gpt-4o")
        self.api_key = ai_config.get("api_key", "")
        self.base_url = ai_config.get("base_url", "https://api.openai.com/v1")
        self.max_tokens = self._validate_max_tokens(ai_config.get("max_tokens", 2000))
        self.temperature = self._validate_temperature(ai_config.get("temperature", 0.7))
        self.context_max_messages = self._validate_context(ai_config.get("context_max_messages", 50))
        self._client = None
        self._init_client()

    @staticmethod
    def _validate_max_tokens(value) -> int:
        try:
            val = int(value)
        except (TypeError, ValueError):
            print(f"[AI] 警告：max_tokens 值无效 ({value})，已使用默认值 2000")
            return 2000
        if val < 1 or val > 128000:
            clamped = min(max(val, 1), 128000)
            print(f"[AI] 警告：max_tokens 值 {val} 超出范围，已钳制为 {clamped}")
            return clamped
        return val

    @staticmethod
    def _validate_temperature(value) -> float:
        try:
            val = float(value)
        except (TypeError, ValueError):
            return 0.7
        return max(min(val, 2.0), 0.0)

    @staticmethod
    def _validate_context(value) -> int:
        """校验上下文最大消息数（2-200）"""
        try:
            val = int(value)
        except (TypeError, ValueError):
            return 50
        return max(2, min(val, 200))

    def _trim_messages(self, messages: list) -> list:
        """截断消息列表至 context_max_messages 条（保留 system 消息）"""
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]
        if len(other_msgs) > self.context_max_messages:
            trimmed = other_msgs[-self.context_max_messages:]
            return system_msgs + trimmed
        return messages

    def _init_client(self):
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self._init_error = None
        except ImportError as e:
            self._init_error = f"openai 库未安装: {e}"
            print(f"[AI] 警告：{self._init_error}")
            self._client = None
        except Exception as e:
            self._init_error = f"初始化 OpenAI 客户端失败: {e}"
            print(f"[AI] 警告：{self._init_error}")
            self._client = None

    def validate(self):
        """返回 (成功:bool, 消息:str)"""
        if self._client is None:
            return False, self._init_error or "AI 客户端未初始化"
        try:
            self._client.models.list()
            return True, "连接成功"
        except Exception as e:
            err = str(e)
            if "401" in err or "Unauthorized" in err:
                msg = "API Key 无效，请检查 config.yaml 中的 api_key"
            elif "404" in err or "Not Found" in err:
                msg = f"API 地址无法访问，请检查 base_url"
            elif "Connection" in err or "connect" in err:
                msg = f"无法连接 API 服务，请检查网络或 base_url"
            else:
                msg = f"验证失败: {err[:200]}"
            print(f"[AI] {msg}")
            return False, msg

    # ==================== 流式对话（含工具调用循环）====================

    def chat_stream(self, messages: list):
        """流式对话生成器，自动处理工具调用循环

        Yields:
            {"type": "content", "text": "..."}  — 文本增量
            {"type": "tool_call", "name": "...", "arguments": {...}}  — 工具调用
            {"type": "tool_result", "name": "...", "result": "..."}  — 工具结果
            {"type": "done"}  — 对话结束
            {"type": "error", "message": "..."}  — 错误
        """
        if self._client is None:
            yield {"type": "error", "message": "AI 客户端未初始化（openai 库可能未安装）"}
            return

        # 前置系统提示词 + 截断历史消息
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        full_messages = self._trim_messages(full_messages)

        max_rounds = 10  # 防止无限循环
        for round_num in range(max_rounds):
            try:
                stream = self._client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    stream=True,
                )
            except Exception as e:
                yield {"type": "error", "message": str(e)}
                return

            # 收集流式输出
            content_buffer = ""
            tool_calls_buffer = {}  # {index: {id, name, arguments_str}}

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 文本内容
                if delta.content:
                    content_buffer += delta.content
                    yield {"type": "content", "text": delta.content}

                # 工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments_str": ""
                            }
                        if tc.id:
                            tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["arguments_str"] += tc.function.arguments

            # 处理工具调用
            if tool_calls_buffer:
                # 把 AI 的 assistant message 加入历史
                assistant_msg = {"role": "assistant", "content": content_buffer or None}
                if content_buffer:
                    assistant_msg["content"] = content_buffer
                else:
                    assistant_msg["content"] = None

                # 构建 tool_calls 数组
                tool_calls_list = []
                for idx in sorted(tool_calls_buffer.keys()):
                    tc = tool_calls_buffer[idx]
                    try:
                        args = json.loads(tc["arguments_str"]) if tc["arguments_str"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls_list.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments_str"]
                        }
                    })
                    yield {"type": "tool_call", "name": tc["name"], "arguments": args}

                assistant_msg["tool_calls"] = tool_calls_list
                full_messages.append(assistant_msg)

                # 执行每个工具并返回结果
                for tc in tool_calls_list:
                    try:
                        args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    result = execute_tool(tc["function"]["name"], args)
                    yield {"type": "tool_result", "name": tc["function"]["name"], "result": result}

                    full_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                # 继续循环，让 AI 处理工具结果
                continue

            # 没有工具调用，正常结束
            yield {"type": "done"}
            return

        # 超过最大轮数
        yield {"type": "error", "message": "达到最大工具调用轮数（10轮），对话终止"}

    # ==================== 普通非流式对话（兼容旧接口）====================

    def chat(self, messages: list) -> str:
        """非流式对话（兼容旧接口）"""
        if self._client is None:
            raise RuntimeError("AI 客户端未初始化（openai 库可能未安装）")
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content
