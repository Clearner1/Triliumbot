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

    # ASR语音识别配置
    DOUBAO_APP_KEY = os.getenv('DOUBAO_APP_KEY')
    DOUBAO_ACCESS_KEY = os.getenv('DOUBAO_ACCESS_KEY')
    ASR_ENABLED = os.getenv('ASR_ENABLED', 'false').lower() == 'true'

    # 日志配置
    LOG_LEVEL = logging.INFO  # 正常日志级别

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
    """设置日志 - 仅输出到控制台，不保存到文件"""
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()  # 仅输出到控制台，不写文件
        ]
    )

    return logging.getLogger(__name__)