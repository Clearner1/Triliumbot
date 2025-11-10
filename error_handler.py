import logging
import functools
import traceback
import asyncio
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class BotError(Exception):
    """Bot基础异常类"""
    def __init__(self, message, error_code=None, original_error=None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error
        self.timestamp = datetime.now()

class TriliumConnectionError(BotError):
    """Trilium连接错误"""
    pass

class TelegramConnectionError(BotError):
    """Telegram连接错误"""
    pass

class MessageProcessingError(BotError):
    """消息处理错误"""
    pass

class ConfigurationError(BotError):
    """配置错误"""
    pass

def error_handler(func):
    """错误处理装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BotError as e:
            logger.error(f"业务错误 [{func.__name__}]: {e}")
            # 可以根据错误类型返回不同的用户提示
            raise
        except Exception as e:
            logger.error(f"未知错误 [{func.__name__}]: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise MessageProcessingError("处理消息时发生未知错误，请稍后重试")
    return wrapper

def safe_execute(func, default_return=None, log_error=True):
    """安全执行函数"""
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"执行函数 {func.__name__} 失败: {e}")
        return default_return

class ErrorReporter:
    """错误报告器"""

    def __init__(self):
        self.error_counts = {}
        self.last_error_report = {}

    def report_error(self, error_type: str, error_message: str, context: dict = None):
        """报告错误"""
        timestamp = datetime.now()

        # 记录错误计数
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # 检查是否需要发送报告（避免重复报告）
        last_report = self.last_error_report.get(error_type)
        if last_report and (timestamp - last_report).seconds < 300:  # 5分钟内不重复报告
            return

        # 记录错误报告时间
        self.last_error_report[error_type] = timestamp

        # 构建错误报告
        report = {
            'timestamp': timestamp,
            'error_type': error_type,
            'error_message': error_message,
            'count': self.error_counts[error_type],
            'context': context or {}
        }

        # 记录日志
        logger.error(f"错误报告: {report}")

        # 这里可以添加发送通知的逻辑，比如发送到管理员
        # await self.send_notification_to_admin(report)

    def get_error_stats(self):
        """获取错误统计"""
        return {
            'error_counts': self.error_counts.copy(),
            'total_errors': sum(self.error_counts.values())
        }

class RetryHandler:
    """重试处理器"""

    def __init__(self, max_retries=3, delay=1):
        self.max_retries = max_retries
        self.delay = delay

    async def retry_async(self, func, *args, **kwargs):
        """异步重试执行"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.warning(f"重试第 {attempt} 次: {func.__name__}")
                    await asyncio.sleep(self.delay * attempt)  # 递增延迟

                return await func(*args, **kwargs)

            except Exception as e:
                last_error = e
                logger.error(f"第 {attempt + 1} 次尝试失败: {e}")

                if attempt == self.max_retries:
                    break

                # 根据错误类型决定是否继续重试
                if isinstance(e, (ConfigurationError, TelegramConnectionError)):
                    logger.error(f"错误类型不适合重试: {type(e).__name__}")
                    break

        logger.error(f"所有重试都失败了: {func.__name__}")
        raise last_error

    def retry_sync(self, func, *args, **kwargs):
        """同步重试执行"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.warning(f"重试第 {attempt} 次: {func.__name__}")
                    time.sleep(self.delay * attempt)

                return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                logger.error(f"第 {attempt + 1} 次尝试失败: {e}")

                if attempt == self.max_retries:
                    break

                if isinstance(e, (ConfigurationError, TelegramConnectionError)):
                    logger.error(f"错误类型不适合重试: {type(e).__name__}")
                    break

        logger.error(f"所有重试都失败了: {func.__name__}")
        raise last_error

# 全局错误报告器实例
error_reporter = ErrorReporter()

def handle_trilium_error(func):
    """Trilium错误处理装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_type = "TriliumConnectionError" if "connection" in str(e).lower() else "TriliumError"
            error_reporter.report_error(error_type, str(e), {'function': func.__name__})
            raise TriliumConnectionError(f"Trilium操作失败: {e}", original_error=e)
    return wrapper

def handle_telegram_error(func):
    """Telegram错误处理装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_type = "TelegramError"
            error_reporter.report_error(error_type, str(e), {'function': func.__name__})
            raise TelegramConnectionError(f"Telegram操作失败: {e}", original_error=e)
    return wrapper