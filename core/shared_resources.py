"""共享图片资源管理器 —— 单例模式，所有猫咪共用"""

import os
from . import constants


class SharedResources:
    """所有猫共享的图片资源（单例模式）"""
    _loaded = False
    cat_dict = {}               # {文件夹名: [文件名列表]}
    default_static_path = ""

    @classmethod
    def load(cls, base_dir=None):
        if cls._loaded:
            return
        if base_dir is None:
            base_dir = constants.IMAGE_BASE_DIR
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
        cls.default_static_path = os.path.join(base_dir, constants.DEFAULT_STATIC_IMAGE)
        if not os.path.exists(cls.default_static_path):
            print(f"警告：默认静态图片 {constants.DEFAULT_STATIC_IMAGE} 不存在！")
        cls._loaded = True
