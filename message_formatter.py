import re
from datetime import datetime
from utils import get_local_time

class MessageFormatter:
    """消息格式化器"""

    @staticmethod
    def format_diary_entry(message_text, message_type='text', metadata=None):
        """
        格式化日记条目

        Args:
            message_text: 消息文本
            message_type: 消息类型 (text, photo, document, voice, location)
            metadata: 额外的元数据字典
        """
        if metadata is None:
            metadata = {}

        current_time = get_local_time().strftime('%H:%M:%S')

        # 根据消息类型选择不同的格式
        if message_type == 'text':
            return MessageFormatter._format_text_entry(message_text, current_time, metadata)
        elif message_type == 'photo':
            return MessageFormatter._format_photo_entry(message_text, current_time, metadata)
        elif message_type == 'document':
            return MessageFormatter._format_document_entry(message_text, current_time, metadata)
        elif message_type == 'voice':
            return MessageFormatter._format_voice_entry(message_text, current_time, metadata)
        elif message_type == 'location':
            return MessageFormatter._format_location_entry(message_text, current_time, metadata)
        else:
            return MessageFormatter._format_text_entry(message_text, current_time, metadata)

    @staticmethod
    def _format_text_entry(text, time, metadata):
        """格式化文本条目"""
        # 提取标签
        hashtags = re.findall(r'#(\w+)', text)

        # 移除标签前的文本，重新组织
        clean_text = text

        # 构建条目
        entry = f"## {time}\n\n{clean_text}"

        if hashtags:
            entry += f"\n\n🏷️ 标签: {', '.join(['#' + tag for tag in hashtags])}"

        return entry, hashtags

    @staticmethod
    def _format_photo_entry(caption, time, metadata):
        """格式化图片条目"""
        hashtags = re.findall(r'#(\w+)', caption) if caption else []

        entry = f"## {time}\n\n📷 图片"

        if caption:
            entry += f"\n\n描述: {caption}"

        if metadata.get('file_name'):
            entry += f"\n\n文件: {metadata['file_name']}"

        if hashtags:
            entry += f"\n\n🏷️ 标签: {', '.join(['#' + tag for tag in hashtags])}"

        return entry, hashtags

    @staticmethod
    def _format_document_entry(caption, time, metadata):
        """格式化文档条目"""
        hashtags = re.findall(r'#(\w+)', caption) if caption else []

        entry = f"## {time}\n\n📄 文档"

        file_name = metadata.get('file_name', '未知文件')
        entry += f"\n\n文件名: {file_name}"

        if caption:
            entry += f"\n\n描述: {caption}"

        file_size = metadata.get('file_size')
        if file_size:
            entry += f"\n大小: {MessageFormatter._format_file_size(file_size)}"

        if hashtags:
            entry += f"\n\n🏷️ 标签: {', '.join(['#' + tag for tag in hashtags])}"

        return entry, hashtags

    @staticmethod
    def _format_voice_entry(caption, time, metadata):
        """格式化语音条目"""
        hashtags = re.findall(r'#(\w+)', caption) if caption else []

        entry = f"## {time}\n\n🎤 语音消息"

        duration = metadata.get('duration')
        if duration:
            entry += f"\n\n时长: {duration}秒"

        if caption:
            entry += f"\n\n备注: {caption}"

        if hashtags:
            entry += f"\n\n🏷️ 标签: {', '.join(['#' + tag for tag in hashtags])}"

        return entry, hashtags

    @staticmethod
    def _format_location_entry(caption, time, metadata):
        """格式化位置条目"""
        hashtags = re.findall(r'#(\w+)', caption) if caption else []

        entry = f"## {time}\n\n📍 位置"

        latitude = metadata.get('latitude')
        longitude = metadata.get('longitude')

        if latitude and longitude:
            entry += f"\n\n坐标: {latitude}, {longitude}"
            # 可以添加Google Maps链接
            entry += f"\n\n[地图链接](https://maps.google.com/maps?q={latitude},{longitude})"

        if caption:
            entry += f"\n\n备注: {caption}"

        if hashtags:
            entry += f"\n\n🏷️ 标签: {', '.join(['#' + tag for tag in hashtags])}"

        return entry, hashtags

    @staticmethod
    def _format_file_size(size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f}{size_names[i]}"

    @staticmethod
    def extract_smart_hashtags(text):
        """智能提取标签，包括一些常见的模式"""
        hashtags = re.findall(r'#(\w+)', text)

        # 添加一些智能标签提取逻辑
        # 检测工作相关关键词
        work_keywords = ['工作', '项目', '会议', '任务', '完成', '开发', '编程']
        for keyword in work_keywords:
            if keyword in text and 'work' not in hashtags:
                hashtags.append('work')

        # 检测生活相关关键词
        life_keywords = ['生活', '心情', '天气', '吃饭', '朋友', '家人']
        for keyword in life_keywords:
            if keyword in text and 'life' not in hashtags:
                hashtags.append('life')

        # 检测学习相关关键词
        study_keywords = ['学习', '读书', '课程', '知识', '笔记']
        for keyword in study_keywords:
            if keyword in text and 'study' not in hashtags:
                hashtags.append('study')

        return list(set(hashtags))  # 去重

    @staticmethod
    def format_diary_title(date=None):
        """格式化日记标题"""
        if date is None:
            date = get_local_time()

        return f"日记 - {date.strftime('%Y-%m-%d')}"

    @staticmethod
    def create_separator():
        """创建条目分隔符"""
        return "\n" + "─" * 50 + "\n"