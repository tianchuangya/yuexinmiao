"""路径工具 —— 同时兼容开发环境和 PyInstaller 打包环境"""

import os
import sys


def _is_frozen() -> bool:
    """是否在 PyInstaller 打包环境中运行"""
    return getattr(sys, 'frozen', False)


def get_project_root() -> str:
    """项目根目录（开发环境返回源码目录，打包环境返回 exe 所在目录）"""
    if _is_frozen():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """只读数据目录（image/、skill/ 等随包资源）"""
    if _is_frozen():
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_path() -> str:
    """配置文件路径（可读写，在 exe 同级目录）"""
    return os.path.join(get_project_root(), "config.yaml")


def get_conversations_dir() -> str:
    """对话存储目录（可读写）"""
    return os.path.join(get_project_root(), "conversations")


def get_skill_dir() -> str:
    """Skill 目录（可读写）"""
    return os.path.join(get_project_root(), "skill")


def get_skill_file() -> str:
    """Skill 文件路径"""
    return os.path.join(get_skill_dir(), "skill.md")


def get_image_dir() -> str:
    """图片资源目录（只读，随包）"""
    # 先检查项目根目录（用户可能覆盖），再检查打包数据目录
    root_img = os.path.join(get_project_root(), "image")
    if os.path.exists(root_img):
        return root_img
    return os.path.join(get_data_dir(), "image")
