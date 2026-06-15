"""配置文件加载、保存与验证模块"""

import os
import yaml
from .paths import get_config_path

CONFIG_PATH = get_config_path()

DEFAULT_CONFIG = {
    "ai": {
        "model": "gpt-4o",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "max_tokens": 2000,
        "temperature": 0.7,
        "context_max_messages": 50,
    },
    "app": {
        "image_base_dir": "image",
        "startup_gif": "休闲/冒泡.gif",
        "default_static_image": "yuexinmiao.png",
        "base_switch_probability": 50,
        "probability_increment": 25,
        "max_probability": 100,
        "fixed_image_size": 100,
        "num_cats": 1,
        "move_speed_min": -3,
        "move_speed_max": 3,
    },
}


def load_config() -> dict:
    """加载配置文件，不存在则用默认值创建"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    # 合并默认值（保证新增字段有默认值）
    merged = _deep_merge(DEFAULT_CONFIG, config)
    return merged


def save_config(config: dict) -> None:
    """保存配置到 yaml 文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_ai_config() -> dict:
    """获取 AI 子配置"""
    return load_config().get("ai", {})


def get_app_config() -> dict:
    """获取 App 子配置"""
    return load_config().get("app", {})


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base 中的值"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
