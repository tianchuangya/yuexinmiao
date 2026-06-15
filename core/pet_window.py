"""桌面宠物窗口 —— 猫咪主体，含双击对话和 AI 交互"""

import os
import random
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QMenu, QMessageBox
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QMovie, QPixmap

from . import constants
from .shared_resources import SharedResources
from .cat_state import CatState


class PetWindow(QWidget):
    """桌面宠物主窗口"""
    chat_requested = pyqtSignal(object)   # 双击时发出，传递自身引用

    def __init__(self, cat_id=0, base_dir=None):
        super().__init__()
        self.cat_id = cat_id
        self.base_dir = base_dir or constants.IMAGE_BASE_DIR
        self.state = CatState()
        self.current_movie = None
        self.switch_timer = QTimer(self)
        self.oldPos = None
        self.label = None
        self._chat_input = None       # 关联的 ChatInput 引用
        self._input_offset = None     # 输入框相对于猫咪的偏移 (dx, dy)
        self._ai_client = None        # AI 客户端（由 app 注入）
        self._skill_manager = None    # Skill 管理器（由 app 注入）
        self._conversation = None     # 当前对话对象
        self._pre_ai_state = None     # AI 开始前的图片状态 (folder, filename, full_path)
        self._ai_thinking = False     # AI 是否正在思考

        SharedResources.load(self.base_dir)
        self.initUI()
        self.start_with_bubble()

    # ==================== 公开方法 ====================

    def set_ai_client(self, client):
        """注入 AI 客户端"""
        self._ai_client = client

    def set_skill_manager(self, manager):
        """注入 Skill 管理器"""
        self._skill_manager = manager

    def set_conversation(self, conversation):
        """注入当前对话对象"""
        self._conversation = conversation

    # ==================== UI 初始化 ====================

    def initUI(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setScaledContents(False)

        screen = QApplication.primaryScreen().geometry()
        temp_w = constants.FIXED_IMAGE_SIZE if constants.FIXED_IMAGE_SIZE > 0 else 200
        temp_h = temp_w
        max_x = max(0, screen.width() - temp_w)
        max_y = max(0, screen.height() - temp_h)
        x = random.randint(0, max_x) if max_x > 0 else 0
        y = random.randint(0, max_y) if max_y > 0 else 0
        self.move(x, y)
        self.resize(temp_w, temp_h)

    # ==================== 时间段判断 ====================

    def is_night_time(self):
        return datetime.now().hour >= 20

    # ==================== 随机选择图片 ====================

    def get_random_image_info(self):
        """返回 (文件夹名, 文件名, 完整路径)"""
        candidate_folders = list(SharedResources.cat_dict.keys())
        if not self.is_night_time():
            candidate_folders = [f for f in candidate_folders if f != "晚上"]
        if not candidate_folders:
            candidate_folders = list(SharedResources.cat_dict.keys())
        folder = random.choice(candidate_folders)
        filename = random.choice(SharedResources.cat_dict[folder])
        full_path = os.path.join(self.base_dir, folder, filename)
        return folder, filename, full_path

    # ==================== 显示静态图片 ====================

    def show_static_image(self, image_path):
        self.stop_moving()
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
            self.current_movie = None
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.label.setPixmap(pixmap)
            self._apply_size_constraints(pixmap.size())
        else:
            print(f"[猫{self.cat_id}] 无法加载图片: {image_path}")

    # ==================== 显示 GIF ====================

    def show_gif(self, gif_path):
        self.stop_moving()
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
        self.current_movie = QMovie(gif_path)
        self._current_gif_path = gif_path    # 记录路径以便恢复
        self.label.setMovie(self.current_movie)
        self.current_movie.start()
        QTimer.singleShot(50, lambda: self._apply_size_constraints(
            self.current_movie.currentPixmap().size() if self.current_movie else None))

    def _apply_size_constraints(self, original_size=None):
        if constants.FIXED_IMAGE_SIZE > 0:
            self.label.setFixedSize(constants.FIXED_IMAGE_SIZE, constants.FIXED_IMAGE_SIZE)
            self.label.setScaledContents(True)
            self.resize(constants.FIXED_IMAGE_SIZE, constants.FIXED_IMAGE_SIZE)
        else:
            if original_size and not original_size.isNull():
                self.label.resize(original_size.width(), original_size.height())
                self.resize(original_size.width(), original_size.height())
            else:
                self.resize(200, 200)
            self.label.setScaledContents(False)

    # ==================== 切换逻辑 ====================

    def attempt_switch(self):
        r = random.randint(1, 100)
        if r <= self.state.current_probability:
            print(f"[猫{self.cat_id}] 触发切换（概率 {self.state.current_probability}%）")
            self.state.reset_probability()
            self.perform_switch()
        else:
            self.state.increase_probability()
            print(f"[猫{self.cat_id}] 未切换，下次概率 {self.state.current_probability}%")

    def perform_switch(self):
        folder, filename, full_path = self.get_random_image_info()
        print(f"[猫{self.cat_id}] 切换图片：{folder}/{filename}")

        if folder == "移动":
            self.show_static_image(full_path)
            self.start_moving()
        else:
            if filename.lower().endswith('.gif'):
                self.show_gif(full_path)
            else:
                self.show_static_image(full_path)
            self.stop_moving()

    # ==================== 移动模式 ====================

    def start_moving(self):
        if self.state.is_moving:
            return
        self.state.is_moving = True
        speeds = [v for v in range(constants.MOVE_SPEED_MIN, constants.MOVE_SPEED_MAX + 1) if v != 0]
        if not speeds:
            speeds = [3, -3]
        self.state.move_dx = random.choice(speeds)
        self.state.move_dy = random.choice(speeds)
        self.state.move_timer = QTimer(self)
        self.state.move_timer.timeout.connect(self.move_step)
        self.state.move_timer.start(20)

    def stop_moving(self):
        if self.state.move_timer:
            self.state.move_timer.stop()
            self.state.move_timer.deleteLater()
            self.state.move_timer = None
        self.state.is_moving = False

    def move_step(self):
        if not self.state.is_moving:
            return
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()
        new_x = x + self.state.move_dx
        new_y = y + self.state.move_dy

        if new_x <= screen_geo.left():
            new_x = screen_geo.left()
            self.state.move_dx = -self.state.move_dx
        if new_x + w >= screen_geo.right():
            new_x = screen_geo.right() - w
            self.state.move_dx = -self.state.move_dx
        if new_y <= screen_geo.top():
            new_y = screen_geo.top()
            self.state.move_dy = -self.state.move_dy
        if new_y + h >= screen_geo.bottom():
            new_y = screen_geo.bottom() - h
            self.state.move_dy = -self.state.move_dy

        self.move(new_x, new_y)
        # 通知输入框跟随
        self._notify_input_follow()

    # ==================== 启动流程 ====================

    def start_with_bubble(self):
        bubble_path = os.path.join(self.base_dir, constants.STARTUP_GIF)
        if os.path.exists(bubble_path):
            self.show_gif(bubble_path)
        else:
            print(f"[猫{self.cat_id}] 启动GIF不存在，直接显示默认图片")
        QTimer.singleShot(3000, self.switch_to_default)

    def switch_to_default(self):
        default_path = SharedResources.default_static_path
        if os.path.exists(default_path):
            self.show_static_image(default_path)
        else:
            self.perform_switch()
        self.switch_timer.timeout.connect(self.attempt_switch)
        self.switch_timer.start(60000)

    # ==================== 鼠标事件 ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos is not None:
            delta = event.globalPos() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()
            self._notify_input_follow()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def mouseDoubleClickEvent(self, event):
        """双击猫咪：打开/关闭输入框"""
        if event.button() == Qt.LeftButton:
            self._toggle_chat_input()

    def contextMenuEvent(self, event):
        """右键菜单：退出确认"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a35;
                color: #eee;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4a4a60;
            }
        """)

        # 标题项（不可点击）
        title_action = menu.addAction("是否要退出？")
        title_action.setEnabled(False)
        menu.addSeparator()

        yes_action = menu.addAction("  ✓ 是 —— 保存并退出")
        no_save_action = menu.addAction("  ✗ 否 —— 不保存退出")
        cancel_action = menu.addAction("  ← 取消")

        action = menu.exec_(event.globalPos())

        if action == yes_action:
            self._on_exit_confirmed()
        elif action == no_save_action:
            self._close_chat_input()
            QApplication.quit()
        # cancel_action 不做任何事

    # ==================== 输入框管理 ====================

    def _toggle_chat_input(self):
        """切换输入框显示/隐藏"""
        if self._chat_input is not None:
            self._close_chat_input()
        else:
            self._open_chat_input()

    def _open_chat_input(self):
        """创建并显示浮动输入框"""
        if not constants.AI_ENABLED:
            QMessageBox.information(self, "提示",
                "AI 功能未启用。\n请检查 config.yaml 中的 api_key 和 base_url 配置是否正确。")
            return

        from ui.chat_input import ChatInput

        self._chat_input = ChatInput(parent_cat=self)
        self._chat_input.message_submitted.connect(self._on_chat_send)
        self._chat_input.switch_conversation.connect(self._switch_to_conversation)
        self._chat_input.new_conversation_requested.connect(self._on_new_conversation)

        # 加载已有的对话消息到视图
        if self._conversation and self._conversation.messages:
            self._chat_input.load_messages(self._conversation.messages)
            self._chat_input.set_conversation_info(
                self._conversation.id, self._conversation.get_title())

        self._position_input_near_cat()
        self._chat_input.show()

    def _position_input_near_cat(self):
        """将输入框定位在猫咪左侧或右侧（选空间更大的一侧）"""
        if self._chat_input is None:
            return
        screen = QApplication.primaryScreen().availableGeometry()
        cat_geo = self.geometry()
        input_w, input_h = 320, 200  # ChatInput 默认大小

        space_left = cat_geo.left() - screen.left()
        space_right = screen.right() - cat_geo.right()

        if space_right >= space_left:
            # 放在右边
            input_x = cat_geo.right() + 5
        else:
            # 放在左边
            input_x = cat_geo.left() - input_w - 5

        input_y = cat_geo.top()
        # 确保不超出屏幕
        input_x = max(screen.left(), min(input_x, screen.right() - input_w))
        input_y = max(screen.top(), min(input_y, screen.bottom() - input_h))

        self._chat_input.move(input_x, input_y)
        # 记录偏移量（相对于猫咪左上角）
        self._input_offset = (input_x - cat_geo.left(), input_y - cat_geo.top())

    def _notify_input_follow(self):
        """通知输入框跟随猫咪位置"""
        if self._chat_input is None or self._input_offset is None:
            return
        dx, dy = self._input_offset
        self._chat_input.move(self.x() + dx, self.y() + dy)

    def _close_chat_input(self):
        """关闭输入框（线程安全）"""
        ci = self._chat_input
        if ci is not None:
            self._chat_input = None
            self._input_offset = None
            ci.close()
            ci.deleteLater()

    # ==================== AI 对话处理（流式 + 工具调用循环）====================

    def _enter_ai_thinking(self):
        """AI 开始思考：冻结移动，切换到「工作」图片"""
        if self._ai_thinking:
            return
        self._ai_thinking = True

        # 保存当前图片状态
        self._pre_ai_state = self._capture_image_state()

        # 停止移动
        self.stop_moving()

        # 暂停切换定时器
        self.switch_timer.stop()

        # 切换到「工作」文件夹中的随机 GIF
        work_files = SharedResources.cat_dict.get("工作", [])
        if work_files:
            gif = random.choice(work_files)
            gif_path = os.path.join(self.base_dir, "工作", gif)
            self.show_gif(gif_path)
            print(f"[猫{self.cat_id}] AI思考中 → 工作动画: {gif}")

    def _exit_ai_thinking(self):
        """AI 思考结束：恢复之前的图片状态"""
        if not self._ai_thinking:
            return
        self._ai_thinking = False

        # 恢复切换定时器
        self.switch_timer.start(60000)

        # 恢复之前的图片
        if self._pre_ai_state:
            self._restore_image_state(self._pre_ai_state)
            self._pre_ai_state = None
            print(f"[猫{self.cat_id}] AI思考结束 → 恢复原图")

    def _capture_image_state(self) -> dict:
        """捕获当前显示的图片状态"""
        state = {"type": "none"}
        if self.current_movie and self.current_movie.state() == QMovie.Running:
            # 当前正在播放 GIF
            state["type"] = "gif"
            # 取当前的图片路径（从 SharedResources 中找到）
            state["gif_path"] = getattr(self, '_current_gif_path', None)
        else:
            # 显示静态图
            state["type"] = "static"
        return state

    def _restore_image_state(self, state: dict):
        """恢复图片状态"""
        if state.get("type") == "gif" and state.get("gif_path"):
            self.show_gif(state["gif_path"])
        else:
            # 恢复默认静态图
            default_path = SharedResources.default_static_path
            if os.path.exists(default_path):
                self.show_static_image(default_path)

    def _on_chat_send(self, text: str):
        """处理用户发送的消息（流式输出 + 自动工具调用）"""
        if not self._ai_client or not self._conversation:
            QMessageBox.warning(self, "错误", "AI 客户端未初始化，无法发送消息。")
            return

        # 进入 AI 思考状态（冻结移动、切换工作图）
        self._enter_ai_thinking()

        # 添加到对话数据
        self._conversation.add_message("user", text)

        # 在聊天界面中显示用户消息
        if self._chat_input:
            self._chat_input.add_user_message(text)

        # 准备消息列表
        skill_context = self._skill_manager.get_context() if self._skill_manager else ""
        messages = self._conversation.get_messages_for_api(skill_context)

        # 开始流式输出
        if self._chat_input:
            self._chat_input.begin_stream()

        # 使用 QTimer 在事件循环中处理流式数据
        self._process_stream(messages)

    def _process_stream(self, messages: list):
        """在事件循环中逐步处理流式数据"""
        try:
            stream_gen = self._ai_client.chat_stream(messages)
            self._handle_stream_chunk(stream_gen)
        except Exception as e:
            if self._chat_input:
                self._chat_input.end_stream(f"请求失败: {str(e)}")
            QMessageBox.warning(self, "AI 错误", f"请求失败：{str(e)}\n\n请检查网络连接和 API 配置。")
            self._exit_ai_thinking()

    def _handle_stream_chunk(self, stream_gen):
        """处理一个流式数据块，然后用 QTimer 调度下一个"""
        try:
            chunk = next(stream_gen)
        except StopIteration:
            return
        except Exception as e:
            if self._chat_input:
                self._chat_input.end_stream(f"流式处理错误: {str(e)}")
            self._exit_ai_thinking()
            return

        chunk_type = chunk.get("type")

        if chunk_type == "content":
            if self._chat_input:
                self._chat_input.append_stream_chunk(chunk["text"])

        elif chunk_type == "tool_call":
            name = chunk.get("name", "?")
            if self._chat_input:
                self._chat_input.append_stream_chunk(f"\n\n🔧 **调用工具: {name}**...")

        elif chunk_type == "tool_result":
            name = chunk.get("name", "?")
            result = chunk.get("result", "")
            if self._chat_input:
                self._chat_input.append_tool_info(name, result)

        elif chunk_type == "done":
            # 流式输出完成
            final_text = self._chat_input._stream_buffer if self._chat_input else ""
            if self._conversation:
                self._conversation.add_message("assistant", final_text)
                self._conversation.save()
            if self._chat_input:
                self._chat_input.end_stream()
                self._chat_input.set_conversation_info(
                    self._conversation.id, self._conversation.get_title())
            # 更新 Skill
            if self._skill_manager and self._conversation:
                self._skill_manager.summarize_and_append(self._conversation)
            # 退出 AI 思考状态
            self._exit_ai_thinking()
            return

        elif chunk_type == "error":
            error_msg = chunk.get("message", "未知错误")
            if self._chat_input:
                self._chat_input.end_stream(error_msg)
            QMessageBox.warning(self, "AI 错误", f"{error_msg}\n\n请检查网络连接和 API 配置。")
            self._exit_ai_thinking()
            return

        # 让事件循环先处理完待处理事件（GIF 动画等），再处理下一块
        QApplication.processEvents()
        QTimer.singleShot(0, lambda: self._handle_stream_chunk(stream_gen))

    # ==================== 会话管理 ====================

    def _switch_to_conversation(self, conv_id: str):
        """切换会话：先保存当前，再加载目标"""
        # 保存当前对话
        if self._conversation and self._conversation.messages:
            self._conversation.save()
            print(f"[会话] 已保存: {self._conversation.id}")

        # 加载目标对话
        from ai.conversation import Conversation
        try:
            new_conv = Conversation.load(conv_id)
        except FileNotFoundError:
            QMessageBox.warning(self, "错误", f"会话文件不存在: {conv_id}")
            return

        self._conversation = new_conv
        print(f"[会话] 已切换到: {conv_id} ({new_conv.get_title()})")

        # 刷新聊天视图
        if self._chat_input:
            self._chat_input.load_messages(new_conv.messages)
            self._chat_input.set_conversation_info(conv_id, new_conv.get_title())

    def _on_new_conversation(self):
        """新建对话：先保存当前，创建新的"""
        if self._conversation and self._conversation.messages:
            self._conversation.save()
            print(f"[会话] 已保存: {self._conversation.id}")

        from ai.conversation import Conversation
        self._conversation = Conversation()
        print(f"[会话] 新建: {self._conversation.id}")

        if self._chat_input:
            self._chat_input.load_messages([])
            self._chat_input.set_conversation_info(
                self._conversation.id, "新对话")

    # ==================== 资源销毁 ====================

    def _on_exit_confirmed(self):
        """用户确认退出：保存对话→更新Skill→退出"""
        import shutil
        status_parts = []

        # 保存当前对话
        if self._conversation and self._conversation.messages:
            self._conversation.save()

            # 按"总结+日期"命名，移动到子文件夹
            title = self._conversation.get_title(max_len=20)
            date_str = datetime.now().strftime("%Y%m%d")
            safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()[:20]
            folder_name = f"{safe_title}_{date_str}"
            conv_dir = os.path.join("conversations", folder_name)
            os.makedirs(conv_dir, exist_ok=True)

            src = os.path.join("conversations", f"{self._conversation.id}.json")
            dst = os.path.join(conv_dir, f"{self._conversation.id}.json")
            try:
                shutil.move(src, dst)
                status_parts.append(f"对话已保存至 {folder_name}")
                print(f"[退出] 对话已保存至: {conv_dir}")
            except OSError:
                status_parts.append("历史对话已保存")
                print(f"[退出] 对话已保存: {self._conversation.id}")

        # 更新 Skill
        if self._skill_manager and self._conversation and self._conversation.messages:
            self._skill_manager.summarize_and_append(self._conversation)
            status_parts.append("Skill 已更新")
            print("[退出] Skill 已更新")

        if status_parts:
            QMessageBox.information(self, "退出", "、".join(status_parts) + "\n程序即将退出。")

        self._close_chat_input()
        QApplication.quit()

    def closeEvent(self, event):
        # 保存当前对话
        if self._conversation and self._conversation.messages:
            self._conversation.save()
        self._close_chat_input()
        self.stop_moving()
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
        self.switch_timer.stop()
        self.switch_timer.deleteLater()
        event.accept()
