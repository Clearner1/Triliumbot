#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Trilium Telegram Bot 简化版主程序
"""

import asyncio
import logging
import sys
from config import Config, setup_logging
from telegram_handler import TelegramBotHandler

# 设置日志
logger = setup_logging()

def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("🤖 Trilium Telegram Bot 启动中...")
        logger.info("=" * 50)

        # 验证配置
        Config.validate_config()
        logger.info("✅ 配置验证通过")

        # 初始化Bot处理器
        bot_handler = TelegramBotHandler()
        logger.info("✅ Bot处理器初始化完成")

        # 启动Bot
        logger.info("🚀 Bot 启动成功，开始监听消息...")
        logger.info("发送消息到你的 Telegram Bot 开始使用")
        logger.info("支持命令: /start, /help, /today, /search <关键词>, /recent, /status")

        # 运行Bot (同步方式)
        bot_handler.run_bot()

    except KeyboardInterrupt:
        logger.info("👋 程序已停止")
    except Exception as e:
        logger.error(f"❌ 程序运行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()