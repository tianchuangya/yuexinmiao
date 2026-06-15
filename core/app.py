"""应用启动模块 —— 入口只需调用 start()"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QInputDialog, QMessageBox, QDialog,
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt

from . import constants
from .pet_window import PetWindow
from utils.config import load_config, get_ai_config, get_app_config
from utils.paths import get_image_dir


def start():
    """应用主入口函数"""
    app = QApplication(sys.argv)

    # ---- 加载配置并赋值到 constants ----
    config = load_config()
    app_cfg = config.get("app", {})
    constants.IMAGE_BASE_DIR = app_cfg.get("image_base_dir", get_image_dir())
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

    # ---- 关于弹窗 ----
    _show_about_dialog(ai_enabled)

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

    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())


def _show_about_dialog(ai_enabled: bool):
    """显示关于弹窗（声明 + 博客链接）"""
    dlg = QDialog()
    dlg.setWindowTitle("关于 月星猫")
    dlg.setFixedSize(420, 270)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dlg.setStyleSheet("""
        QDialog { background-color: #2a2a35; }
        QLabel { color: #ddd; font-size: 13px; }
        QPushButton { padding: 6px 20px; }
    """)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 16, 20, 12)
    layout.setSpacing(10)

    # 声明文字
    text1 = QLabel("本应用由 是天创呀 开发")
    text1.setAlignment(Qt.AlignCenter)
    text1.setStyleSheet("font-size: 15px; font-weight: bold; color: #fff;")
    layout.addWidget(text1)

    text2 = QLabel("图片源于网上，免费使用，禁止盗取商用！")
    text2.setAlignment(Qt.AlignCenter)
    text2.setStyleSheet("color: #f80; font-size: 13px;")
    layout.addWidget(text2)

    # 博客链接（可点击）
    link_label = QLabel(
        '<a href="https://tianchuangya.cc/start" style="color: #7af; text-decoration: none;">'
        '🌐 https://tianchuangya.cc/start</a>'
    )
    link_label.setAlignment(Qt.AlignCenter)
    link_label.setOpenExternalLinks(True)
    link_label.setCursor(Qt.PointingHandCursor)
    link_label.setStyleSheet("font-size: 13px;")
    layout.addWidget(link_label)

    # GitHub 开源地址
    github_label = QLabel(
        '<a href="https://github.com/tianchuangya/yuexinmiao" style="color: #8af; text-decoration: none;">'
        '⭐ GitHub 项目开源地址</a>'
    )
    github_label.setAlignment(Qt.AlignCenter)
    github_label.setOpenExternalLinks(True)
    github_label.setCursor(Qt.PointingHandCursor)
    github_label.setStyleSheet("font-size: 13px;")
    layout.addWidget(github_label)

    # 咖啡链接
    coffee_label = QLabel(
        '<a href="https://tianchuangya.cc/money" style="color: #fc8; text-decoration: none;">'
        '☕ 可以请作者喝杯咖啡嘛？</a>'
    )
    coffee_label.setAlignment(Qt.AlignCenter)
    coffee_label.setOpenExternalLinks(True)
    coffee_label.setCursor(Qt.PointingHandCursor)
    coffee_label.setStyleSheet("font-size: 13px;")
    layout.addWidget(coffee_label)

    # AI 状态
    ai_status = QLabel(f"AI 功能：{'✅ 已启用' if ai_enabled else '⚠️ 已禁用（配置无效）'}")
    ai_status.setAlignment(Qt.AlignCenter)
    ai_status.setStyleSheet(f"color: {'#8f8' if ai_enabled else '#f88'}; font-size: 11px;")
    layout.addWidget(ai_status)

    layout.addSpacing(4)

    # 关闭按钮
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    close_btn = QPushButton("开始使用")
    close_btn.setStyleSheet("""
        QPushButton {
            background: rgba(100,160,240,0.8); color: #fff;
            border: none; border-radius: 8px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background: rgba(100,160,240,1); }
    """)
    close_btn.clicked.connect(dlg.accept)
    btn_layout.addWidget(close_btn)
    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    dlg.exec_()


def _validate_ai_config() -> bool:
    """验证 AI 配置是否有效，失败则弹窗提示具体原因"""
    ai_cfg = get_ai_config()
    api_key = ai_cfg.get("api_key", "")

    if not api_key:
        constants.AI_ENABLED = False
        return False

    try:
        from ai.client import AIClient
        client = AIClient(ai_cfg)
        ok, msg = client.validate()
        if ok:
            constants.AI_ENABLED = True
            return True
        else:
            _warn_ai_disabled(msg)
            constants.AI_ENABLED = False
            return False
    except Exception as e:
        _warn_ai_disabled(f"初始化异常：{str(e)}")
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
