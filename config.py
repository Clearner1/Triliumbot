import os
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

class Config:
    """配置管理类"""

    # Telegram配置
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Trilium配置
    TRILIUM_API_TOKEN = os.getenv('TRILIUM_API_TOKEN')
    TRILIUM_SERVER_URL = os.getenv('TRILIUM_SERVER_URL')

    # 日记配置
    DIARY_PARENT_NOTE_ID = os.getenv('DIARY_PARENT_NOTE_ID', '')
    DIARY_TEMPLATE = os.getenv('DIARY_TEMPLATE', '')
    TIMEZONE = os.getenv('TIMEZONE', 'Asia/Shanghai')

    # 日志配置
    LOG_LEVEL = logging.INFO

    @classmethod
    def validate_config(cls):
        """验证必要的配置项"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN 未设置")

        if not cls.TRILIUM_API_TOKEN:
            raise ValueError("TRILIUM_API_TOKEN 未设置")

        if not cls.TRILIUM_SERVER_URL:
            raise ValueError("TRILIUM_SERVER_URL 未设置")

        return True

# 日志配置
def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('telegram_trilium_bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)