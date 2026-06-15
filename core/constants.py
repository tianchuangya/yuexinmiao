"""应用运行时常量 —— 由 config.yaml 加载后赋值"""

# 以下变量在 app.start() 中由 load_config() 赋值
IMAGE_BASE_DIR = "image"
STARTUP_GIF = "休闲/冒泡.gif"
DEFAULT_STATIC_IMAGE = "yuexinmiao.png"
BASE_SWITCH_PROBABILITY = 50
PROBABILITY_INCREMENT = 25
MAX_PROBABILITY = 100
FIXED_IMAGE_SIZE = 100
NUM_CATS = 1
MOVE_SPEED_MIN = -3
MOVE_SPEED_MAX = 3

# AI 功能开关（启动时由 API 验证结果决定）
AI_ENABLED = False
