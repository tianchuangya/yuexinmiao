"""AI 工具集 —— 文件读写、搜索、命令执行

工具定义遵循 OpenAI function calling 格式，
所有文件操作默认限制在项目根目录内以保证安全。
"""

import os
import re
import subprocess
import shutil
import glob as glob_mod
from utils.paths import get_project_root

# 项目根目录（用于路径安全限制）
PROJECT_ROOT = get_project_root()


def _safe_path(file_path: str) -> str:
    """确保路径在项目根目录内，防止路径遍历攻击"""
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, file_path))
    if not abs_path.startswith(os.path.normpath(PROJECT_ROOT)):
        raise ValueError(f"拒绝访问项目目录外的路径: {file_path}")
    return abs_path


# ==================== 工具定义（OpenAI 格式）====================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容。返回带行号的文本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对于项目根目录，如 'main.py' 或 'core/app.py'）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多读取行数，默认2000"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "起始行偏移，默认0"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建或覆盖文件。会自动创建不存在的父目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对于项目根目录）"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的完整内容"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "精确替换文件中的字符串。old_string 必须在文件中唯一匹配。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对于项目根目录）"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "要替换的原始文本（必须与文件中内容完全一致，包含缩进）"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "替换后的新文本"
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录内容（文件和子目录）。默认列出项目根目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径（相对于项目根目录，默认为 '.'）"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "可选的 glob 匹配模式，如 '**/*.py'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "在文件中搜索匹配的文本行（支持正则表达式）。类似 grep。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持正则表达式）"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索目录或文件路径（相对于项目根目录，默认 '.'）"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "文件过滤 glob，如 '*.py'，默认所有文件"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "是否区分大小写，默认 True"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除指定的文件（不可恢复，请谨慎使用）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要删除的文件路径（相对于项目根目录）"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "移动或重命名文件/目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "源路径（相对于项目根目录）"
                    },
                    "destination": {
                        "type": "string",
                        "description": "目标路径（相对于项目根目录）"
                    }
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "执行系统命令并返回标准输出。请谨慎执行破坏性命令。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令。会限制在项目根目录执行，超时60秒。"
                    }
                },
                "required": ["command"]
            }
        }
    }
]


# ==================== 工具实现 ====================

def read_file(file_path: str, limit: int = 2000, offset: int = 0) -> str:
    """读取文件并返回带行号的内容"""
    abs_path = _safe_path(file_path)
    if not os.path.exists(abs_path):
        return f"❌ 文件不存在: {file_path}"
    if os.path.isdir(abs_path):
        return f"❌ 路径是目录而非文件: {file_path}"
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total = len(lines)
        end = min(offset + limit, total)
        selected = lines[offset:end]
        result = []
        for i, line in enumerate(selected, start=offset + 1):
            result.append(f"{i}\t{line.rstrip()}")
        header = f"📄 {file_path}（行 {offset+1}-{end} / 共 {total} 行）\n"
        return header + "\n".join(result)
    except UnicodeDecodeError:
        return f"⚠️ 无法以 UTF-8 编码读取: {file_path}（可能是二进制文件）"
    except Exception as e:
        return f"❌ 读取失败: {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """创建或覆盖文件"""
    abs_path = _safe_path(file_path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        size = len(content)
        lines = content.count('\n') + 1
        return f"✅ 已写入 {file_path}（{lines} 行，{size} 字节）"
    except Exception as e:
        return f"❌ 写入失败: {str(e)}"


def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """精确替换文件中的字符串"""
    abs_path = _safe_path(file_path)
    if not os.path.exists(abs_path):
        return f"❌ 文件不存在: {file_path}"
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"❌ 读取失败: {str(e)}"

    count = content.count(old_string)
    if count == 0:
        return f"❌ 未找到匹配的 old_string，请检查内容是否完全一致（含缩进/换行）"
    if count > 1:
        return f"❌ old_string 匹配了 {count} 处（不唯一），请提供更精确的上下文使其唯一匹配"

    new_content = content.replace(old_string, new_string, 1)
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"✅ 已编辑 {file_path}（1 处替换）"
    except Exception as e:
        return f"❌ 写入失败: {str(e)}"


def list_directory(path: str = ".", pattern: str = None) -> str:
    """列出目录内容"""
    abs_path = _safe_path(path) if path != "." else PROJECT_ROOT
    if not os.path.exists(abs_path):
        return f"❌ 路径不存在: {path}"

    if pattern:
        search = os.path.join(abs_path, pattern)
        results = sorted(glob_mod.glob(search, recursive=True))
        display = []
        for p in results:
            rel = os.path.relpath(p, PROJECT_ROOT)
            marker = "/" if os.path.isdir(p) else ""
            size = ""
            if os.path.isfile(p):
                s = os.path.getsize(p)
                size = f" ({s:,} B)"
            display.append(f"  {rel}{marker}{size}")
        header = f"📂 {path}/{pattern}（{len(results)} 项）\n"
        return header + ("\n".join(display) if display else "  （无匹配项）")
    else:
        if os.path.isfile(abs_path):
            return f"📄 {path} 是一个文件（{os.path.getsize(abs_path):,} B）"
        items = sorted(os.listdir(abs_path))
        dirs = [f"  📁 {d}/" for d in items if os.path.isdir(os.path.join(abs_path, d))]
        files = []
        for f in items:
            fp = os.path.join(abs_path, f)
            if os.path.isfile(fp):
                s = os.path.getsize(fp)
                files.append(f"  📄 {f} ({s:,} B)")
        all_items = dirs + files
        header = f"📂 {path or '.'}/（{len(all_items)} 项）\n"
        return header + "\n".join(all_items[:100])


def search_content(pattern: str, path: str = ".", file_pattern: str = None, case_sensitive: bool = True) -> str:
    """搜索文件内容"""
    abs_path = _safe_path(path) if path != "." else PROJECT_ROOT
    if not os.path.exists(abs_path):
        return f"❌ 路径不存在: {path}"

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"❌ 正则表达式无效: {str(e)}"

    results = []
    if os.path.isfile(abs_path):
        files_to_search = [abs_path]
    else:
        files_to_search = []
        for root, dirs, filenames in os.walk(abs_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git', 'venv', '.conda', 'mooncat_env', 'build', 'dist', '_internal')]
            for fn in filenames:
                if file_pattern and not glob_mod.fnmatch.fnmatch(fn, file_pattern):
                    continue
                if fn.startswith('.'):
                    continue
                files_to_search.append(os.path.join(root, fn))

    for fp in files_to_search[:200]:  # 限制搜索200个文件
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        rel = os.path.relpath(fp, PROJECT_ROOT)
                        results.append(f"  {rel}:{i}: {line.rstrip()[:200]}")
        except (UnicodeDecodeError, PermissionError):
            continue

    if not results:
        return f"🔍 在 {path} 中未找到匹配 '{pattern}' 的内容"
    header = f"🔍 找到 {len(results)} 处匹配 '{pattern}'：\n"
    return header + "\n".join(results[:50])


def delete_file(file_path: str) -> str:
    """删除文件"""
    abs_path = _safe_path(file_path)
    if not os.path.exists(abs_path):
        return f"❌ 文件不存在: {file_path}"
    if os.path.isdir(abs_path):
        return f"❌ 是目录而非文件: {file_path}（请用 execute_command 的 rmdir/rm -rf）"
    try:
        os.remove(abs_path)
        return f"✅ 已删除 {file_path}"
    except Exception as e:
        return f"❌ 删除失败: {str(e)}"


def move_file(source: str, destination: str) -> str:
    """移动/重命名文件或目录"""
    abs_src = _safe_path(source)
    abs_dst = _safe_path(destination)
    if not os.path.exists(abs_src):
        return f"❌ 源路径不存在: {source}"
    try:
        os.makedirs(os.path.dirname(abs_dst), exist_ok=True)
        shutil.move(abs_src, abs_dst)
        return f"✅ 已移动 {source} → {destination}"
    except Exception as e:
        return f"❌ 移动失败: {str(e)}"


def execute_command(command: str) -> str:
    """执行系统命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace"
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += "\n[stderr]\n" + result.stderr.strip()
        if not output:
            output = f"（命令执行完成，返回码 {result.returncode}，无输出）"
        return f"💻 $ {command}\n{output}"
    except subprocess.TimeoutExpired:
        return f"⏰ 命令超时（60秒）: {command}"
    except Exception as e:
        return f"❌ 命令执行失败: {str(e)}"


# ==================== 工具调度 ====================

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_directory": list_directory,
    "search_content": search_content,
    "delete_file": delete_file,
    "move_file": move_file,
    "execute_command": execute_command,
}


def execute_tool(name: str, arguments: dict) -> str:
    """根据工具名和参数执行工具，返回结果字符串"""
    func = TOOL_MAP.get(name)
    if func is None:
        return f"❌ 未知工具: {name}"
    try:
        return func(**arguments)
    except TypeError as e:
        return f"❌ 工具参数错误 ({name}): {str(e)}"
    except Exception as e:
        return f"❌ 工具执行异常 ({name}): {str(e)}"
