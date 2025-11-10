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

def get_time_period(hour):
    """根据小时数返回时间段名称
    
    Args:
        hour: 小时数 (0-23)
        
    Returns:
        str: 时间段名称（凌晨/上午/下午/晚上）
    """
    if 0 <= hour < 6:
        return "🌙 凌晨 (00:00-06:00)"
    elif 6 <= hour < 12:
        return "🌅 上午 (06:00-12:00)"
    elif 12 <= hour < 18:
        return "☀️ 下午 (12:00-18:00)"
    else:
        return "🌆 晚上 (18:00-24:00)"

def get_hour_section(hour):
    """获取小时段标题
    
    Args:
        hour: 小时数 (0-23)
        
    Returns:
        str: 小时段标题，例如 "09:00", "14:00"
    """
    return f"{hour:02d}:00"

def check_section_exists(content, section_title):
    """检查笔记内容中是否已存在指定的标题
    
    Args:
        content: 笔记HTML内容
        section_title: 要检查的标题文本
        
    Returns:
        bool: 如果存在返回True，否则False
    """
    # 检查各级标题
    patterns = [
        f'<h1>{section_title}</h1>',
        f'<h2>{section_title}</h2>',
        f'<h3>{section_title}</h3>',
    ]
    return any(pattern in content for pattern in patterns)

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