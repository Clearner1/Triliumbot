import datetime
from dateutil import tz
import re

def get_local_time():
    """获取本地时间"""
    local_tz = tz.gettz('Asia/Shanghai')
    return datetime.datetime.now(local_tz)

def format_diary_date(date=None):
    """格式化日记日期"""
    if date is None:
        date = get_local_time()
    return date.strftime("%Y-%m-%d")

def format_diary_title(date=None):
    """格式化日记标题"""
    if date is None:
        date = get_local_time()
    return f"日记 - {format_diary_date(date)}"

def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def extract_hashtags(text):
    """从文本中提取标签"""
    hashtags = re.findall(r'#(\w+)', text)
    return hashtags

def format_message_content(message, hashtags=None):
    """格式化消息内容为日记格式"""
    if hashtags is None:
        hashtags = []

    # 提取消息中的标签
    message_hashtags = extract_hashtags(message)
    all_hashtags = list(set(hashtags + message_hashtags))

    # 构建日记内容
    content = f"## {get_local_time().strftime('%H:%M:%S')}\n\n"
    content += f"{message}\n\n"

    # 添加标签
    if all_hashtags:
        content += "标签: " + ", ".join([f"#{tag}" for tag in all_hashtags]) + "\n"

    return content, all_hashtags