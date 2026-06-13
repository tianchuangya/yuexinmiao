import sys
import random
import os
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QMovie, QPixmap

# ======================== 用户配置区 ========================
IMAGE_BASE_DIR = "image"                # 图片根目录
STARTUP_GIF = os.path.join("休闲", "冒泡.gif")   # 启动时强制显示的GIF
DEFAULT_STATIC_IMAGE = "yuexinmiao.png"  # 默认静态图
BASE_SWITCH_PROBABILITY = 50            # 基础切换概率（%）
PROBABILITY_INCREMENT = 25              # 未触发时增加的概率（%）
MAX_PROBABILITY = 100                   # 最大概率上限
FIXED_IMAGE_SIZE = 100                    # 0=自适应图片原始尺寸；>0=固定正方形边长
NUM_CATS = 1                            # 同时运行的桌宠数量
MOVE_SPEED_RANGE = (-3, 3)              # 移动速度范围（像素/20ms，排除0）
# ============================================================

class SharedResources:
    """所有猫共享的图片资源（单例模式）"""
    _loaded = False
    cat_dict = {}               # {文件夹名: [文件名列表]}
    default_static_path = ""

    @classmethod
    def load(cls, base_dir):
        if cls._loaded:
            return
        print("正在加载共享图片资源...")
        if not os.path.exists(base_dir):
            print(f"警告：目录 {base_dir} 不存在！")
            cls._loaded = True
            return
        for folder_name in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, folder_name)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path) if f.lower().endswith('.gif')]
                if files:
                    cls.cat_dict[folder_name] = files
                    print(f"  - 文件夹 [{folder_name}]：{len(files)} 个GIF")
        cls.default_static_path = os.path.join(base_dir, DEFAULT_STATIC_IMAGE)
        if not os.path.exists(cls.default_static_path):
            print(f"警告：默认静态图片 {DEFAULT_STATIC_IMAGE} 不存在！")
        cls._loaded = True


class CatState:
    """每只猫的独立状态"""
    def __init__(self):
        self.current_probability = BASE_SWITCH_PROBABILITY
        self.is_moving = False
        self.move_dx = 0
        self.move_dy = 0
        self.move_timer = None

    def reset_probability(self):
        self.current_probability = BASE_SWITCH_PROBABILITY

    def increase_probability(self):
        self.current_probability += PROBABILITY_INCREMENT
        if self.current_probability > MAX_PROBABILITY:
            self.current_probability = MAX_PROBABILITY


class PetWindow(QWidget):
    def __init__(self, cat_id=0, base_dir=IMAGE_BASE_DIR):
        super().__init__()
        self.cat_id = cat_id
        self.base_dir = base_dir
        self.state = CatState()
        self.current_movie = None
        self.switch_timer = QTimer(self)
        self.oldPos = None
        self.label = None

        # 确保共享资源已加载
        SharedResources.load(base_dir)

        self.initUI()
        self.start_with_bubble()

    # ---------- UI 初始化 ----------
    def initUI(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setScaledContents(False)

        # 随机初始位置（屏幕内）
        screen = QApplication.primaryScreen().geometry()
        # 临时大小，实际大小将由后续图片决定
        temp_w = FIXED_IMAGE_SIZE if FIXED_IMAGE_SIZE > 0 else 200
        temp_h = temp_w
        max_x = max(0, screen.width() - temp_w)
        max_y = max(0, screen.height() - temp_h)
        x = random.randint(0, max_x) if max_x > 0 else 0
        y = random.randint(0, max_y) if max_y > 0 else 0
        self.move(x, y)
        self.resize(temp_w, temp_h)

    # ---------- 时间段判断 ----------
    def is_night_time(self):
        return datetime.now().hour >= 20

    # ---------- 随机选择图片 ----------
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

    # ---------- 显示静态图片 ----------
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

    # ---------- 显示GIF ----------
    def show_gif(self, gif_path):
        self.stop_moving()
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
        self.current_movie = QMovie(gif_path)
        self.label.setMovie(self.current_movie)
        self.current_movie.start()
        # 延迟获取GIF第一帧尺寸
        QTimer.singleShot(50, lambda: self._apply_size_constraints(
            self.current_movie.currentPixmap().size() if self.current_movie else None))

    def _apply_size_constraints(self, original_size=None):
        """根据 FIXED_IMAGE_SIZE 调整窗口和标签大小"""
        if FIXED_IMAGE_SIZE > 0:
            # 固定大小模式
            self.label.setFixedSize(FIXED_IMAGE_SIZE, FIXED_IMAGE_SIZE)
            self.label.setScaledContents(True)
            self.resize(FIXED_IMAGE_SIZE, FIXED_IMAGE_SIZE)
        else:
            # 自适应模式
            if original_size and not original_size.isNull():
                self.label.resize(original_size.width(), original_size.height())
                self.resize(original_size.width(), original_size.height())
            else:
                # 保底尺寸
                self.resize(200, 200)
            self.label.setScaledContents(False)

    # ---------- 切换逻辑（概率累积）----------
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
            # 移动文件夹：假设图片为静态图，并启动移动
            self.show_static_image(full_path)
            self.start_moving()
        else:
            if filename.lower().endswith('.gif'):
                self.show_gif(full_path)
            else:
                self.show_static_image(full_path)
            self.stop_moving()

    # ---------- 移动模式 ----------
    def start_moving(self):
        if self.state.is_moving:
            return
        self.state.is_moving = True
        # 随机速度（排除0）
        low, high = MOVE_SPEED_RANGE
        speeds = [v for v in range(low, high+1) if v != 0]
        if not speeds:
            speeds = [3, -3]   # 保底
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

        # 边界反弹
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

    # ---------- 启动流程 ----------
    def start_with_bubble(self):
        bubble_path = os.path.join(self.base_dir, STARTUP_GIF)
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
            self.perform_switch()   # 应急
        # 启动每分钟切换定时器
        self.switch_timer.timeout.connect(self.attempt_switch)
        self.switch_timer.start(60000)

    # ---------- 鼠标拖拽 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.oldPos is not None:
            delta = event.globalPos() - self.oldPos
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    # ---------- 资源销毁 ----------
    def closeEvent(self, event):
        self.stop_moving()
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie.deleteLater()
        self.switch_timer.stop()
        self.switch_timer.deleteLater()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 弹出对话框让用户输入参数
    from PyQt5.QtWidgets import QInputDialog, QMessageBox
    
    # 默认值
    default_num_cats = NUM_CATS  # 从配置区获取的默认值
    default_base_prob = BASE_SWITCH_PROBABILITY
    default_inc = PROBABILITY_INCREMENT
    
    # 输入猫的数量
    num_cats_str, ok1 = QInputDialog.getInt(app.activeWindow(), "参数设置", "猫的数量 (NUM_CATS):", value=default_num_cats, min=1, max=100)
    if not ok1:
        sys.exit(0)
    NUM_CATS = num_cats_str
    
    base_prob, ok2 = QInputDialog.getInt(app.activeWindow(), "参数设置", "基础切换概率 (BASE_SWITCH_PROBABILITY, %):", value=default_base_prob, min=0, max=100)
    if not ok2:
        sys.exit(0)
    BASE_SWITCH_PROBABILITY = base_prob
    
    inc, ok3 = QInputDialog.getInt(app.activeWindow(), "参数设置", "未触发时增加的概率 (PROBABILITY_INCREMENT, %):", value=default_inc, min=0, max=100)
    if not ok3:
        sys.exit(0)
    PROBABILITY_INCREMENT = inc
    
    # 可选：提示用户设置已生效
    QMessageBox.information(None, "提示", f"参数已设置：\n猫数量={NUM_CATS}\n基础概率={BASE_SWITCH_PROBABILITY}%\n增量={PROBABILITY_INCREMENT}%")
    
    # 然后原有的创建窗口循环
    windows = []
    for i in range(NUM_CATS):
        pet = PetWindow(cat_id=i+1)
        pet.show()
        windows.append(pet)
    
    app.lastWindowClosed.connect(app.quit)
    sys.exit(app.exec_())