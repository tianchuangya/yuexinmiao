# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

月星猫（MoonStar Cat）桌面桌宠应用，基于 PyQt5 构建。支持多只猫咪同时显示 GIF 动画、定时随机切换、边界反弹移动、鼠标拖拽，以及双击猫咪打开 AI 对话输入框（支持 OpenAI 兼容 API）。

## 常用命令

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行应用
```bash
python main.py
```

### 打包为 exe（PyInstaller）
```bash
venv\Scripts\activate
pyinstaller --windowed --icon="favicon.ico" --add-data "image;image" --add-data "config.yaml;." --add-data "skill;skill" --add-data "conversations;conversations" main.py
```

## 模块架构

项目采用模块化架构，入口 `main.py` 仅一行调用，所有逻辑按功能分包：

```
├── main.py                       # 入口：from core.app import start; start()
├── config.yaml                   # 用户配置（AI密钥、模型参数、桌宠参数）
├── core/                         # 核心逻辑
│   ├── app.py                    # start() 启动函数：加载配置→验证AI→创建窗口
│   ├── constants.py              # 运行时全局常量（由config.yaml赋值）
│   ├── shared_resources.py       # SharedResources 单例：加载image/下GIF文件
│   ├── cat_state.py              # CatState：每只猫的概率/移动状态
│   └── pet_window.py             # PetWindow：猫咪窗口主体+鼠标事件+AI对话交互
├── ai/                           # AI 模块
│   ├── client.py                 # AIClient：OpenAI兼容API封装（validate + chat）
│   ├── conversation.py           # Conversation：对话JSON存储（add/load/save/list_all）
│   └── skill_manager.py          # SkillManager：对话总结→skill.md融合精简
├── ui/                           # UI 组件
│   └── chat_input.py             # ChatInput：浮动输入框（Ctrl+Enter发送，跟随猫咪）
├── utils/
│   └── config.py                 # config.yaml 加载/保存/深度合并
├── conversations/                # 对话历史JSON存储目录
├── skill/                        # AI Skill上下文目录
│   └── skill.md                  # 累积精简的对话总结
└── image/                        # GIF图片资源（按行为分文件夹）
    ├── yuexinmiao.png
    ├── 休闲/（25个GIF）
    ├── 吃饭/（1个GIF）
    ├── 天气/（2个GIF）
    ├── 工作/（11个GIF）
    ├── 晚上/（5个GIF，20:00后出现）
    ├── 爱心/（4个GIF）
    └── 移动/（5个GIF，触发壁面反弹移动）
```

## 关键设计

### 概率累积切换
每分钟 `attempt_switch()`：基础概率50%，未触发+25%，触发后重置。保证必有限时间内切换，避免过于频繁。

### AI功能启动流程
`app.start()` → 加载 config.yaml → `AIClient.validate()` 连通性测试 → 失败则 QMessageBox 警告 + `AI_ENABLED=False`，纯本地功能正常运行。

### 双击对话交互
双击猫咪 → `mouseDoubleClickEvent` 触发 → 检查 `AI_ENABLED` → 创建 `ChatInput` 浮动窗口（选左右空间大的一侧定位）→ Ctrl+Enter 发送 → `PetWindow._on_chat_send()` 调用 AI → 回复显示在输入框下方气泡 → 保存到 `conversations/{id}.json` → `SkillManager.summarize_and_append()` 更新 skill.md。

### Skill 融合精简策略
每次对话后，当前 skill 内容 + 本轮对话摘要追加到 skill.md。超3000字时裁剪前半部分，保持紧凑。

### Conversation JSON 结构
```json
{
  "id": "conv_20260615_143021_a1b2c3",
  "created_at": "2026-06-15T14:30:21",
  "updated_at": "2026-06-15T14:35:00",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ]
}
```

## 配置说明 (config.yaml)

| 路径 | 默认值 | 说明 |
|------|--------|------|
| `ai.model` | `"gpt-4o"` | AI 模型名称 |
| `ai.api_key` | `""` | API Key（空则跳过AI功能） |
| `ai.base_url` | `"https://api.openai.com/v1"` | API地址（支持第三方兼容） |
| `ai.max_tokens` | `2000` | 单次回复最大token |
| `ai.temperature` | `0.7` | 生成温度 |
| `app.base_switch_probability` | `50` | 基础切换概率(%) |
| `app.probability_increment` | `25` | 未切换增量(%) |
| `app.num_cats` | `1` | 猫咪数量 |
| `app.fixed_image_size` | `100` | 固定边长(0=自适应) |

**config.yaml 已加入 .gitignore，保护 API Key 安全。**
