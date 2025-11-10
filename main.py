#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Trilium Telegram Bot 主程序
用于将Telegram消息保存到Trilium日记的机器人
"""

import logging
import signal
import sys
from config import Config, setup_logging
from telegram_handler import TelegramBotHandler

# 设置日志
logger = setup_logging()

class TriliumTelegramBot:
    """主应用程序类"""

    def __init__(self):
        self.bot_handler = None
        self.is_running = False

    def start(self):
        """启动应用程序"""
        try:
            logger.info("=" * 50)
            logger.info("🤖 Trilium Telegram Bot 启动中...")
            logger.info("=" * 50)

            # 验证配置
            Config.validate_config()
            logger.info("✅ 配置验证通过")

            # 初始化Bot处理器
            self.bot_handler = TelegramBotHandler()
            logger.info("✅ Bot处理器初始化完成")

            # 启动Bot
            self.is_running = True
            logger.info("🚀 Bot 启动成功，开始监听消息...")

            # 设置信号处理
            self.setup_signal_handlers()

            # 运行Bot (这是同步的，阻塞的)
            self.bot_handler.run_bot()

        except KeyboardInterrupt:
            logger.info("👋 收到中断信号，正在关闭Bot...")
            self.stop()
        except Exception as e:
            logger.error(f"❌ 启动失败: {e}")
            self.stop()
            sys.exit(1)

    def stop(self):
        """停止应用程序"""
        if self.is_running:
            self.is_running = False
            logger.info("🛑 Trilium Telegram Bot 已停止")

    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭...")
            self.stop()
            # 引发 KeyboardInterrupt 来终止程序
            import os
            os.kill(os.getpid(), signal.SIGINT)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    """主函数"""
    try:
        # 创建应用实例
        app = TriliumTelegramBot()

        # 启动应用 (同步方式)
        app.start()

    except KeyboardInterrupt:
        logger.info("👋 程序已停止")
    except Exception as e:
        logger.error(f"程序运行异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()