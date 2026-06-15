快速开始：
1. 安装依赖：pip install -r requirements.txt
2. 配置 config.yaml 中的 API Key（可选，仅 AI 对话功能需要）
3. 运行：python main.py

模块结构：
├── main.py                 # 程序入口
├── config.yaml             # 用户配置文件
├── core/                   # 核心模块（宠物窗口、资源管理、状态）
├── ai/                     # AI 模块（客户端、对话管理、Skill）
├── ui/                     # UI 组件（浮动输入框）
├── utils/                  # 工具（配置加载）
├── conversations/          # 对话历史 JSON
├── skill/                  # AI Skill 上下文
└── image/                  # 图片资源

关于打包：
cmd输入 venv\Scripts\activate 进入虚拟环境之后
输入 pyinstaller --windowed --icon="favicon.ico" --add-data "image;image" --add-data "config.yaml;." --add-data "skill;skill" --add-data "conversations;conversations" main.py
进行打包，生成文件在dist里，需手动配备 image 图像资源

灵感来自网络热门桌宠"月星猫"
动画素材来源于网络（仅供学习交流，禁止倒卖收费）
