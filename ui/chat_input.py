"""浮动输入框 —— 双击猫咪出现，完整聊天界面含会话列表"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QLabel, QHBoxLayout, QFrame, QScrollArea, QListWidget,
    QListWidgetItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap


class ChatInput(QWidget):
    """浮动对话输入框"""
    message_submitted = pyqtSignal(str)
    switch_conversation = pyqtSignal(str)    # 请求切换到指定会话ID
    new_conversation_requested = pyqtSignal()  # 请求新建对话

    def __init__(self, parent_cat=None):
        super().__init__()
        self._parent_cat = parent_cat
        self._loading = False
        self._stream_buffer = ""
        self._reply_widget = None
        self._reply_text = None
        self._conv_list_widget = None   # 会话列表面板
        self._messages_displayed = []   # 已显示的 {role, content}，用于重建视图

        # 头像路径
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._avatar_path = os.path.join(_root, "image", "yuexinmiao.png")

        self._init_ui()

    # ==================== 头像 ====================

    def _make_avatar(self, size: int) -> QLabel:
        label = QLabel()
        if os.path.exists(self._avatar_path):
            p = QPixmap(self._avatar_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(p)
        label.setFixedSize(size + 2, size + 2)
        label.setStyleSheet("background: transparent;")
        return label

    # ==================== UI 初始化 ====================

    def _init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 200)
        self.setMinimumSize(300, 180)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        self._container = QFrame(self)
        self._container.setStyleSheet("QFrame { background-color: rgba(40,40,50,220); border-radius: 10px; }")
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(8, 6, 8, 6)
        container_layout.setSpacing(4)

        # --- 标题栏 ---
        title_layout = QHBoxLayout()
        title_layout.setSpacing(6)

        self._title_avatar = self._make_avatar(18)
        self._title_avatar.mouseDoubleClickEvent = self._on_avatar_double_click
        title_layout.addWidget(self._title_avatar)

        self._title_label = QLabel("对话")
        self._title_label.setStyleSheet("color: #ccc; font-size: 11px; background: transparent;")
        title_layout.addWidget(self._title_label)

        # 新建对话按钮
        new_btn = QPushButton("+")
        new_btn.setFixedSize(20, 20)
        new_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.1); color: #aaa; border: none; border-radius: 10px; font-size: 14px; }
            QPushButton:hover { background: rgba(100,200,100,0.5); color: #fff; }
        """)
        new_btn.clicked.connect(self._on_new_conversation)
        title_layout.addWidget(new_btn)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888; font-size: 10px; background: transparent;")
        title_layout.addWidget(self._status_label)
        title_layout.addStretch()
        container_layout.addLayout(title_layout)

        # --- 输入区 ---
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("输入消息...\nCtrl+Enter 发送 | Enter 换行")
        self._text_edit.setStyleSheet("""
            QTextEdit { background-color: rgba(30,30,40,200); color: #eee; border: 1px solid #555;
                border-radius: 6px; padding: 4px 6px; font-size: 13px; }
            QTextEdit:focus { border-color: #7af; }
        """)
        self._text_edit.setMaximumHeight(60)
        self._text_edit.setMinimumHeight(32)
        container_layout.addWidget(self._text_edit)

        # --- 按钮栏 ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self._loading_label = QLabel("")
        self._loading_label.setStyleSheet("color: #fa0; font-size: 12px; background: transparent;")
        self._loading_label.setVisible(False)
        btn_layout.addWidget(self._loading_label)
        btn_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.1); color: #aaa; border: none; border-radius: 12px; font-size: 13px; }
            QPushButton:hover { background: rgba(255,80,80,0.6); color: #fff; }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        send_btn = QPushButton("发送")
        send_btn.setFixedSize(48, 24)
        send_btn.setStyleSheet("""
            QPushButton { background: rgba(100,160,240,0.7); color: #fff; border: none; border-radius: 12px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: rgba(100,160,240,0.9); }
            QPushButton:pressed { background: rgba(60,120,200,0.9); }
        """)
        send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(send_btn)
        container_layout.addLayout(btn_layout)

        main_layout.addWidget(self._container)

    # ==================== 键盘事件 ====================

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ControlModifier:
                self._on_send()
                return
        super().keyPressEvent(event)

    # ==================== 发送 ====================

    def _on_send(self):
        text = self._text_edit.toPlainText().strip()
        if not text:
            return
        self._text_edit.clear()
        self._text_edit.setEnabled(False)
        self.message_submitted.emit(text)

    # ==================== 会话列表 ====================

    def _on_avatar_double_click(self, event):
        """双击头像：切换会话列表显示"""
        if self._conv_list_widget:
            self._hide_conv_list()
        else:
            self._show_conv_list()

    def _show_conv_list(self):
        """显示会话列表面板"""
        from ai.conversation import Conversation
        conversations = Conversation.list_all()

        self._conv_list_widget = QFrame()
        self._conv_list_widget.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self._conv_list_widget.setAttribute(Qt.WA_TranslucentBackground)
        self._conv_list_widget.setFixedSize(380, 380)

        # 容器
        inner = QFrame(self._conv_list_widget)
        inner.setStyleSheet("QFrame { background-color: rgba(35,35,48,235); border-radius: 10px; }")
        inner.setGeometry(4, 4, 372, 372)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        hdr = QLabel("📋 页面管理")
        hdr.setStyleSheet("color: #ccc; font-size: 12px; font-weight: bold; background: transparent;")
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        header_layout.addWidget(hdr)
        header_layout.addStretch()
        # 关闭按钮
        close_panel_btn = QPushButton("✕")
        close_panel_btn.setFixedSize(22, 22)
        close_panel_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.08); color: #aaa; border: none; border-radius: 11px; font-size: 12px; }
            QPushButton:hover { background: rgba(255,60,60,0.5); color: #fff; }
        """)
        close_panel_btn.clicked.connect(lambda: self._hide_conv_list())
        header_layout.addWidget(close_panel_btn)
        layout.addLayout(header_layout)

        # 可滚动列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: rgba(0,0,0,0.2); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.35); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #ddd; font-size: 12px; }
            QListWidget::item { padding: 4px 2px; border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 4px; }
            QListWidget::item:hover { background: rgba(255,255,255,0.08); }
            QListWidget::item:selected { background: rgba(100,160,240,0.3); }
        """)
        list_widget.setSpacing(1)

        for conv in conversations:
            cid = conv["id"]
            title = conv.get("title", "新对话")
            created = conv.get("created_at", "")[:10] if conv.get("created_at") else ""
            count = conv.get("message_count", 0)

            # 自定义 item widget（多行标题，不截断）
            item_widget = QFrame()
            item_widget.setStyleSheet("QFrame { background: transparent; }")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 8, 8, 8)
            item_layout.setSpacing(8)

            # 文本区域
            text_layout = QVBoxLayout()
            text_layout.setSpacing(4)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("color: #eee; font-size: 13px; font-weight: bold; background: transparent;")
            title_lbl.setWordWrap(True)
            title_lbl.setMinimumHeight(36)
            title_lbl.setCursor(Qt.PointingHandCursor)
            text_layout.addWidget(title_lbl)
            info_lbl = QLabel(f"{created}  ·  {count} 条消息")
            info_lbl.setStyleSheet("color: #888; font-size: 11px; background: transparent; padding-top: 2px;")
            info_lbl.setCursor(Qt.PointingHandCursor)
            text_layout.addWidget(info_lbl)

            # 点击文字区域切换会话
            def make_click_handler(cid):
                def handler(ev):
                    self.switch_conversation.emit(cid)
                    self._hide_conv_list()
                return handler
            click_handler = make_click_handler(cid)
            title_lbl.mousePressEvent = click_handler
            info_lbl.mousePressEvent = click_handler

            item_layout.addLayout(text_layout, 1)

            # 删除按钮
            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(22, 22)
            del_btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.05); color: #999; border: none; border-radius: 11px; font-size: 12px; }
                QPushButton:hover { background: rgba(255,60,60,0.5); color: #fff; }
            """)
            del_btn.setToolTip("删除此会话")
            del_btn.clicked.connect(lambda checked, cid=cid: self._delete_conversation(cid))
            item_layout.addWidget(del_btn)

            # 创建 QListWidgetItem 并设置自定义 widget
            item = QListWidgetItem()
            item.setData(Qt.UserRole, cid)
            # 固定最小高度避免重叠
            hint = item_widget.sizeHint()
            if hint.height() < 56:
                hint.setHeight(56)
            item.setSizeHint(hint)
            list_widget.addItem(item)
            list_widget.setItemWidget(item, item_widget)

        # 注意：itemClicked 不再连接，由自定义 mousePressEvent 处理点击切换
        scroll.setWidget(list_widget)
        layout.addWidget(scroll)

        # 定位会话列表
        self._position_popup(self._conv_list_widget, 380, 380)
        self._conv_list_widget.show()

    def _hide_conv_list(self):
        if self._conv_list_widget:
            self._conv_list_widget.close()
            self._conv_list_widget.deleteLater()
            self._conv_list_widget = None

    def _on_conv_item_clicked(self, item: QListWidgetItem):
        conv_id = item.data(Qt.UserRole)
        self.switch_conversation.emit(conv_id)
        self._hide_conv_list()

    def _delete_conversation(self, conv_id: str):
        """删除指定会话"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除此会话吗？\n\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        from ai.conversation import Conversation
        Conversation.delete(conv_id)
        # 刷新列表
        self._hide_conv_list()
        self._show_conv_list()

    def _on_new_conversation(self):
        self.new_conversation_requested.emit()

    def _position_popup(self, popup, w, h):
        """将弹出面板定位在输入框旁边"""
        screen = self.screen().availableGeometry()
        geo = self.geometry()
        space_right = screen.right() - geo.right()
        if space_right >= w + 10:
            px = geo.right() + 5
        else:
            px = geo.left() - w - 5
        py = geo.top()
        px = max(screen.left(), min(px, screen.right() - w))
        py = max(screen.top(), min(py, screen.bottom() - h))
        popup.move(px, py)

    # ==================== 完整对话视图 ====================

    def _ensure_reply_area(self):
        """确保回复区域已创建"""
        if self._reply_widget is not None:
            return

        self._reply_widget = QFrame(self._container)
        self._reply_widget.setStyleSheet("QFrame { background-color: rgba(50,55,70,200); border-radius: 8px; }")
        reply_layout = QVBoxLayout(self._reply_widget)
        reply_layout.setContentsMargins(6, 4, 6, 4)
        reply_layout.setSpacing(6)

        # 只读滚动聊天区
        self._reply_text = QTextEdit()
        self._reply_text.setReadOnly(True)
        self._reply_text.setStyleSheet("""
            QTextEdit { background-color: transparent; color: #eee; border: none; font-size: 12px; }
            QScrollBar:vertical { background: rgba(0,0,0,0.2); width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.25); border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.4); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._reply_text.setMinimumHeight(100)
        self._reply_text.setMaximumHeight(250)
        reply_layout.addWidget(self._reply_text)

        layout = self._container.layout()
        layout.insertWidget(layout.count() - 1, self._reply_widget)
        self.setFixedHeight(420)

    # ==================== 消息显示 ====================

    def load_messages(self, messages: list):
        """加载完整对话历史到视图"""
        self._ensure_reply_area()
        self._messages_displayed = [{"role": m["role"], "content": m["content"]} for m in messages]
        self._render_all_messages()

    def _render_all_messages(self):
        """渲染全部已显示消息为 HTML"""
        if not self._reply_text:
            return
        html = ""
        for msg in self._messages_displayed:
            if msg["role"] == "user":
                html += self._format_user_msg(msg["content"])
            else:
                html += self._format_ai_msg(msg["content"])
        self._reply_text.setHtml(html)
        sb = self._reply_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _format_user_msg(self, content: str) -> str:
        esc = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<div style="margin:6px 2px; padding:6px 10px; background:rgba(60,100,180,0.25); '
            f'border-radius:8px; border-left:3px solid #6af;">'
            f'<div style="color:#8cf; font-size:10px; margin-bottom:2px;">👤 你</div>'
            f'<div style="color:#eee; white-space:pre-wrap;">{esc}</div></div>'
        )

    def _format_ai_msg(self, content: str) -> str:
        esc = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<div style="margin:6px 2px; padding:6px 10px; background:rgba(50,60,80,0.25); '
            f'border-radius:8px;">'
            f'<div style="color:#9cf; font-size:10px; margin-bottom:2px;">🐱 AI</div>'
            f'<div style="color:#eee; white-space:pre-wrap;">{esc}</div></div>'
        )

    # ==================== 流式输出 ====================

    def begin_stream(self):
        """开始流式：添加空的 AI 消息占位"""
        self._ensure_reply_area()
        self._stream_buffer = ""
        self._messages_displayed.append({"role": "assistant", "content": ""})
        self._render_all_messages()
        self.set_loading(True)

    def append_stream_chunk(self, text: str):
        """追加流式文本"""
        self._stream_buffer += text
        if self._messages_displayed and self._messages_displayed[-1]["role"] == "assistant":
            self._messages_displayed[-1]["content"] = self._stream_buffer
        self._render_all_messages()

    def append_tool_info(self, tool_name: str, result: str):
        """追加工具信息"""
        info = f"\n\n🔧 调用工具 {tool_name}\n```\n{result[:500]}\n```\n"
        if self._messages_displayed and self._messages_displayed[-1]["role"] == "assistant":
            self._messages_displayed[-1]["content"] += info
        else:
            self._messages_displayed.append({"role": "assistant", "content": info})
        self._stream_buffer = self._messages_displayed[-1]["content"]
        self._render_all_messages()

    def end_stream(self, error_msg: str = None):
        """结束流式"""
        self.set_loading(False)
        if error_msg:
            self._messages_displayed.append({"role": "assistant", "content": f"⚠️ {error_msg}"})
            self._render_all_messages()

    def add_user_message(self, text: str):
        """在视图中添加用户消息"""
        self._ensure_reply_area()
        self._messages_displayed.append({"role": "user", "content": text})
        self._render_all_messages()

    def set_loading(self, loading: bool):
        self._loading = loading
        self._loading_label.setText("⏳ 思考中...")
        self._loading_label.setVisible(loading)
        if not loading:
            self._loading_label.setVisible(False)
            self._text_edit.setEnabled(True)
            self._text_edit.setFocus()

    def set_conversation_info(self, conv_id: str, title: str):
        """更新标题栏显示当前会话信息"""
        short_id = conv_id[-12:] if len(conv_id) > 12 else conv_id
        self._status_label.setText(f"{title[:15]} · {short_id}")

    # ==================== 清理 ====================

    def closeEvent(self, event):
        self._hide_conv_list()
        if self._parent_cat and hasattr(self._parent_cat, '_chat_input'):
            self._parent_cat._chat_input = None
            self._parent_cat._input_offset = None
        super().closeEvent(event)
