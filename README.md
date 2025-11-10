# Trilium Telegram Bot

一个简单的 Telegram Bot，将您的消息自动保存到 Trilium 笔记系统中。

## 快速开始

### 1. 安装依赖
```bash
# Windows用户 - 一键安装
setup.bat

# 或手动安装
pip install -r requirements.txt
```

### 2. 启动程序
```bash
python main.py
```

### 3. 在Telegram中配置
向你的Bot发送任意消息开始使用

## 功能

- 📝 支持文本、图片、文档消息
- 🏷️ 自动提取 #标签
- 📅 按日期自动组织日记
- 🔍 搜索历史日记
- 📊 查看最近日记列表

## 命令

- `/start` - 开始使用
- `/help` - 帮助信息
- `/today` - 查看今日日记
- `/search <关键词>` - 搜索日记
- `/recent` - 最近日记列表
- `/status` - 系统状态

## 配置

配置文件 `.env` 已预设您的信息：
- Telegram Bot Token
- Trilium 服务器地址和API Token

## 日记格式

每个日记笔记按日期创建，消息按时间顺序追加：

```
# 日记 - 2024-01-15

## 09:15:30
今天天气很好，心情不错。

## 10:30:45
工作会议讨论了新项目进展。

## 22:45:30
完成了Python项目的开发。
```

## 项目结构

```
telegram-trilium-bot/
├── main.py                 # 主程序
├── config.py              # 配置管理
├── telegram_handler.py    # Telegram处理
├── trilium_client.py      # Trilium客户端
├── message_formatter.py   # 消息格式化
├── utils.py               # 工具函数
├── error_handler.py       # 错误处理
├── requirements.txt       # 依赖包
├── .env                   # 配置文件
├── .env.example           # 配置模板
├── setup.bat              # 安装脚本
├── run.py                 # 启动脚本
└── README.md              # 说明文档
```

## 故障排除

如果遇到依赖冲突，程序仍可正常运行。核心依赖都已正确安装：
- python-telegram-bot
- trilium-py
- python-dotenv
- requests
- schedule
- python-dateutil

## 使用提示

- 使用 `#标签` 来组织内容
- 图片和文档会自动上传为附件
- 所有消息都会追加到当天的日记中
- 程序运行时会产生日志文件 `telegram_trilium_bot.log`# Triliumbot
