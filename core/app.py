"""应用启动模块 —— 入口只需调用 start()"""

import sys
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox

from . import constants
from .pet_window import PetWindow
from utils.config import load_config, get_ai_config, get_app_config


def start():
    """应用主入口函数"""
    app = QApplication(sys.argv)

    # ---- 加载配置并赋值到 constants ----
    config = load_config()
    app_cfg = config.get("app", {})
    constants.IMAGE_BASE_DIR = app_cfg.get("image_base_dir", "image")
    constants.STARTUP_GIF = app_cfg.get("startup_gif", "休闲/冒泡.gif")
    constants.DEFAULT_STATIC_IMAGE = app_cfg.get("default_static_image", "yuexinmiao.png")
    constants.BASE_SWITCH_PROBABILITY = app_cfg.get("base_switch_probability", 50)
    constants.PROBABILITY_INCREMENT = app_cfg.get("probability_increment", 25)
    constants.MAX_PROBABILITY = app_cfg.get("max_probability", 100)
    constants.FIXED_IMAGE_SIZE = app_cfg.get("fixed_image_size", 100)
    constants.NUM_CATS = app_cfg.get("num_cats", 1)
    constants.MOVE_SPEED_MIN = app_cfg.get("move_speed_min", -3)
    constants.MOVE_SPEED_MAX = app_cfg.get("move_speed_max", 3)

    # ---- 验证 AI 配置 ----
    ai_enabled = _validate_ai_config()

    # ---- 弹出参数对话框 ----
    num_cats, ok1 = QInputDialog.getInt(
        None, "参数设置", "猫的数量 (NUM_CATS):",
        value=constants.NUM_CATS, min=1, max=100
    )
    if not ok1:
        sys.exit(0)
    constants.NUM_CATS = num_cats

    base_prob, ok2 = QInputDialog.getInt(
        None, "参数设置", "基础切换概率 (BASE_SWITCH_PROBABILITY, %):",
        value=constants.BASE_SWITCH_PROBABILITY, min=0, max=100
    )
    if not ok2:
        sys.exit(0)
    constants.BASE_SWITCH_PROBABILITY = base_prob

    inc, ok3 = QInputDialog.getInt(
        None, "参数设置", "未触发时增加的概率 (PROBABILITY_INCREMENT, %):",
        value=constants.PROBABILITY_INCREMENT, min=0, max=100
    )
    if not ok3:
        sys.exit(0)
    constants.PROBABILITY_INCREMENT = inc

    # ---- 初始化 AI 模块（如果配置有效） ----
    ai_client = None
    skill_mgr = None
    if ai_enabled:
        from ai.client import AIClient
        from ai.skill_manager import SkillManager
        ai_cfg = config.get("ai", {})
        ai_client = AIClient(ai_cfg)
        skill_mgr = SkillManager()

    # ---- 创建窗口 ----
    windows = []
    for i in range(constants.NUM_CATS):
        pet = PetWindow(cat_id=i + 1)
        if ai_enabled and ai_client and skill_mgr:
            from ai.conversation import Conversation
            conv = Conversation()
            pet.set_ai_client(ai_client)
            pet.set_skill_manager(skill_mgr)
            pet.set_conversation(conv)
        pet.show()
        windows.append(pet)

    QMessageBox.information(
        None, "提示",
        f"参数已设置：\n猫数量={constants.NUM_CATS}\n"
        f"基础概率={constants.BASE_SWITCH_PROBABILITY}%\n"
        f"增量={constants.PROBABILITY_INCREMENT}%\n"
        f"AI功能={'已启用' if ai_enabled else '已禁用（配置无效）'}"
    )

    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())


def _validate_ai_config() -> bool:
    """验证 AI 配置是否有效，失败则弹窗提示，返回 False"""
    ai_cfg = get_ai_config()
    api_key = ai_cfg.get("api_key", "")
    base_url = ai_cfg.get("base_url", "")

    if not api_key:
        constants.AI_ENABLED = False
        return False

    try:
        from ai.client import AIClient
        client = AIClient(ai_cfg)
        if client.validate():
            constants.AI_ENABLED = True
            return True
        else:
            _warn_ai_disabled("API 验证失败：无法连接到 AI 服务。\n请检查 base_url 和 api_key 是否正确。")
            constants.AI_ENABLED = False
            return False
    except Exception as e:
        _warn_ai_disabled(f"AI 配置验证异常：{str(e)}")
        constants.AI_ENABLED = False
        return False


def _warn_ai_disabled(message: str):
    """弹出 AI 功能禁用警告"""
    try:
        QMessageBox.warning(
            None, "AI 功能已禁用",
            f"{message}\n\nAI 对话功能将在本次运行中跳过。\n"
            "请修改 config.yaml 后重新启动程序。"
        )
    except Exception:
        print(f"[警告] AI 功能已禁用: {message}")
