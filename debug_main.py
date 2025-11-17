#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/root/Triliumbot')

print("开始调试...")

try:
    # 设置基本日志来查看错误
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("开始导入配置...")
    from config import Config, setup_logging
    logger.info("配置导入成功")

    logger.info("验证配置...")
    Config.validate_config()
    logger.info("配置验证成功")

    logger.info("导入TelegramBotHandler...")
    from telegram_handler import TelegramBotHandler
    logger.info("TelegramBotHandler导入成功")

    logger.info("初始化TelegramBotHandler...")
    bot_handler = TelegramBotHandler()
    logger.info("TelegramBotHandler初始化成功")

    logger.info("所有步骤都成功了！")

except Exception as e:
    logger.error(f"发生错误: {e}")
    import traceback
    logger.error(f"详细错误: {traceback.format_exc()}")