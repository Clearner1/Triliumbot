import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from datetime import datetime
import os
import tempfile
import asyncio
import threading
from config import Config
from trilium_client import TriliumClient
from utils import extract_hashtags, format_message_content, get_time_period, get_hour_section, check_section_exists
from asr import DoubaoASRClient

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    """Telegram Bot处理器"""

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.trilium_client = TriliumClient()
        self.allowed_users = []  # 可以在配置中添加允许的用户ID列表
        self.application = None  # 将在run_bot中设置
        self.event_loop = None  # 保存事件循环引用用于后台线程
        
        # 初始化ASR客户端
        if Config.ASR_ENABLED:
            try:
                self.asr_client = DoubaoASRClient(
                    app_key=Config.DOUBAO_APP_KEY,
                    access_key=Config.DOUBAO_ACCESS_KEY
                )
                logger.info("✅ ASR语音识别功能已启用")
            except Exception as e:
                logger.error(f"❌ ASR客户端初始化失败: {e}")
                self.asr_client = None
        else:
            self.asr_client = None
            logger.info("ℹ️ ASR语音识别功能未启用")

    def build_time_hierarchy(self, current_content, current_time):
        """构建时间层次结构
        
        Args:
            current_content: 当前笔记内容
            current_time: datetime对象
            
        Returns:
            str: 需要添加的时间层次标题
        """
        hour = current_time.hour
        time_period = get_time_period(hour)
        hour_section = get_hour_section(hour)
        
        hierarchy = ""
        
        # 检查并添加时间段标题 (H1)
        if not check_section_exists(current_content, time_period):
            hierarchy += f"\n\n<h1>{time_period}</h1>\n"
        
        # 检查并添加小时段标题 (H2)
        if not check_section_exists(current_content, hour_section):
            hierarchy += f"\n<h2>{hour_section}</h2>\n"
        
        return hierarchy

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_message = """
🤖 欢迎使用 Trilium 日记 Bot！

我可以帮助你将 Telegram 消息保存到 Trilium 日记中。

支持的功能：
📝 文本消息 - 直接保存为日记内容
🖼️ 图片 - 保存图片并添加描述
🎤 语音消息 - 保存语音并显示时长
📄 文件 - 保存文件附件
🏷️ 标签 - 使用 #标签 来组织内容

支持的命令：
/help - 显示帮助信息
/today - 查看今日日记
/search <关键词> - 搜索历史日记
/recent - 显示最近日记列表

开始使用吧！直接发送消息即可。
        """
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_text = """
📖 使用帮助

🔸 基本用法：
直接发送消息，系统会自动保存到当天的日记中

🔸 标签功能：
在消息中使用 #标签 来分类内容
例如：今天完成了项目开发 #工作 #编程

🔸 支持的消息类型：
• 文本消息
• 图片（会自动上传并显示）
• 语音消息（会保存并可在Trilium中播放）
• 文件（会自动上传）

🔸 命令列表：
/today - 查看今日日记内容
/search <关键词> - 搜索包含关键词的日记
/recent - 显示最近7天的日记
/status - 查看系统状态
/help - 显示此帮助信息

🔸 示例：
今天天气很好 #生活 #心情
完成了Python项目的开发 #工作 #编程
[发送语音消息] - 自动保存语音并记录时长
        """
        await update.message.reply_text(help_text)

    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /today 命令"""
        try:
            content = self.trilium_client.get_diary_content()
            if content:
                # 限制消息长度，避免超出Telegram限制
                if len(content) > 4000:
                    content = content[:4000] + "\n\n... (内容过长，已截断)"

                await update.message.reply_text(f"📅 今日日记内容：\n\n```\n{content}\n```", parse_mode='Markdown')
            else:
                await update.message.reply_text("📝 今天还没有日记内容，发送消息开始记录吧！")
        except Exception as e:
            logger.error(f"获取今日日记失败: {e}")
            await update.message.reply_text("❌ 获取日记失败，请稍后重试")

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /search 命令"""
        if not context.args:
            await update.message.reply_text("请输入搜索关键词：/search <关键词>")
            return

        keyword = ' '.join(context.args)
        try:
            results = self.trilium_client.search_in_diaries(keyword, limit=5)

            if results:
                response_text = f"🔍 搜索结果 '{keyword}'：\n\n"
                for i, result in enumerate(results, 1):
                    title = result['title']
                    date = result['date']
                    content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                    response_text += f"{i}. {title} ({date})\n{content_preview}\n\n"

                await update.message.reply_text(response_text)
            else:
                await update.message.reply_text(f"没有找到包含 '{keyword}' 的日记")
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            await update.message.reply_text("❌ 搜索失败，请稍后重试")

    async def recent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /recent 命令"""
        try:
            diaries = self.trilium_client.get_recent_diaries(days=7)

            if diaries:
                response_text = "📅 最近的日记：\n\n"
                for diary in diaries:
                    title = diary['title']
                    date = diary['date']
                    response_text += f"📝 {title}\n🗓️ 日期: {date}\n\n"

                await update.message.reply_text(response_text)
            else:
                await update.message.reply_text("还没有日记内容")
        except Exception as e:
            logger.error(f"获取最近日记失败: {e}")
            await update.message.reply_text("❌ 获取日记列表失败")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令"""
        try:
            # 测试Trilium连接
            diaries = self.trilium_client.get_recent_diaries(days=1)
            trilium_status = "✅ 连接正常" if diaries is not None else "❌ 连接异常"

            status_text = f"""
🔧 系统状态

🤖 Bot状态: ✅ 运行中
📝 Trilium连接: {trilium_status}
🗓️ 服务器时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

配置信息：
🔗 Trilium服务器: {Config.TRILIUM_SERVER_URL}
📁 日记父目录: {Config.DIARY_PARENT_NOTE_ID or '根目录'}
🕐 时区: {Config.TIMEZONE}
            """
            await update.message.reply_text(status_text)
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            await update.message.reply_text("❌ 系统状态异常")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息"""
        try:
            message_text = update.message.text
            current_time = datetime.now()

            # 提取标签
            hashtags = extract_hashtags(message_text)

            # 获取日记笔记
            diary_note = self.trilium_client.get_or_create_diary_note()
            note_id = diary_note.get('noteId') if isinstance(diary_note, dict) else diary_note.note_id

            # 获取当前笔记内容
            current_content = self.trilium_client.get_note_content(note_id)

            # 构建时间层次
            new_entry = self.build_time_hierarchy(current_content, current_time)

            # 添加具体时间和内容 (H3)
            time_str = current_time.strftime('%H:%M:%S')
            new_entry += f"\n<h3>{time_str}</h3>\n\n"
            new_entry += f"<p>{message_text}</p>\n\n"

            # 如果有标签，添加到消息中
            if hashtags:
                tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                new_entry += f"<p><strong>标签:</strong> {tags_html}</p>\n"

            # 更新笔记内容
            updated_content = current_content + new_entry
            self.trilium_client.update_note_content(note_id, updated_content)

            # 发送确认消息
            await update.message.reply_text("✅ 消息已保存到日记")

            logger.info(f"用户 {update.effective_user.id} 保存文本消息到日记")

        except Exception as e:
            logger.error(f"处理文本消息失败: {e}")
            await update.message.reply_text("❌ 保存失败，请稍后重试")

    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理图片消息"""
        temp_file_path = None
        try:
            # 获取图片文件
            photo = update.message.photo[-1]  # 获取最大尺寸的图片
            file = await context.bot.get_file(photo.file_id)

            # 下载图片到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file_path = temp_file.name
                await file.download_to_drive(temp_file_path)

            # 构建消息内容
            caption = update.message.caption or "图片"
            hashtags = extract_hashtags(caption)

            # 获取日记笔记
            diary_note = self.trilium_client.get_or_create_diary_note()
            note_id = diary_note.get('noteId') if isinstance(diary_note, dict) else diary_note.note_id

            # 上传图片到Trilium，获取附件ID和HTML
            try:
                attachment_id, image_html = self.trilium_client.upload_attachment(temp_file_path, note_id)
                logger.info(f"图片上传成功: {attachment_id}")

                # 获取当前笔记内容
                current_content = self.trilium_client.get_note_content(note_id)
                current_time = datetime.now()
                
                # 构建时间层次
                new_entry = self.build_time_hierarchy(current_content, current_time)
                
                # 添加具体时间和内容 (H3)
                time_str = current_time.strftime('%H:%M:%S')
                new_entry += f"\n<h3>{time_str}</h3>\n\n"
                
                # 添加图片描述
                if caption and caption != "图片":
                    new_entry += f"<p>{caption}</p>\n\n"
                
                # 添加图片HTML
                new_entry += f"{image_html}\n\n"
                
                # 如果有标签，添加到消息中
                if hashtags:
                    tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                    new_entry += f"<p><strong>标签:</strong> {tags_html}</p>\n"
                
                # 更新笔记内容
                updated_content = current_content + new_entry
                self.trilium_client.update_note_content(note_id, updated_content)
                
                await update.message.reply_text(f"✅ 图片已保存到日记\n📎 附件ID: {attachment_id}")
                logger.info(f"用户 {update.effective_user.id} 保存图片到日记，附件ID: {attachment_id}")

            except Exception as upload_error:
                logger.error(f"上传图片失败: {upload_error}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
                await update.message.reply_text(f"❌ 保存图片失败: {str(upload_error)}")

        except Exception as e:
            logger.error(f"处理图片消息失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            await update.message.reply_text("❌ 保存图片失败，请稍后重试")
        
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"临时文件已删除: {temp_file_path}")
                except Exception as file_error:
                    logger.warning(f"删除临时文件失败: {file_error}")

    def verify_audio_file(self, audio_path):
        """验证音频文件是否有效

        检查音频文件是否存在且大小合理

        Args:
            audio_path: 音频文件路径

        Returns:
            bool: 文件是否有效
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return False

            file_size = os.path.getsize(audio_path)
            if file_size < 100:  # 小于100字节很可能有问题
                logger.warning(f"音频文件过小: {file_size} bytes")
                return False

            logger.info(f"音频文件验证通过: {audio_path}, 大小: {file_size} bytes")
            return True

        except Exception as e:
            logger.error(f"验证音频文件失败: {e}")
            return False
    

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理语音消息"""
        temp_file_path = None
        recognition_file_path = None
        try:
            # 获取语音文件
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)
            
            # 生成带时间戳的文件名
            current_time = datetime.now()
            filename = f"voice_{current_time.strftime('%m-%d-%Y_%H-%M-%S')}.ogg"
            
            # 下载语音文件到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                temp_file_path = temp_file.name
                await file.download_to_drive(temp_file_path)
            
            # 重命名文件为有意义的名称
            final_temp_path = os.path.join(os.path.dirname(temp_file_path), filename)
            os.rename(temp_file_path, final_temp_path)
            temp_file_path = final_temp_path
            
            # 验证音频文件是否有效
            if not self.verify_audio_file(temp_file_path):
                await update.message.reply_text("语音文件无效，请重新发送")
                return
            
            final_filename = os.path.basename(temp_file_path)
            
            # 获取语音时长信息
            duration = voice.duration
            
            # 获取日记笔记
            diary_note = self.trilium_client.get_or_create_diary_note()
            note_id = diary_note.get('noteId') if isinstance(diary_note, dict) else diary_note.note_id
            
            # 上传语音附件（OGG格式）
            try:
                attachment_id, voice_html = self.trilium_client.upload_attachment(temp_file_path, note_id)
                
                file_format = "OGG"
                logger.info(f"语音上传成功: {attachment_id}, 格式: {file_format}, 时长: {duration}秒")
                
                # 获取当前笔记内容
                current_content = self.trilium_client.get_note_content(note_id)
                
                # 构建时间层次
                new_entry = self.build_time_hierarchy(current_content, current_time)
                
                # 添加具体时间和内容 (H3)
                time_str = current_time.strftime('%H:%M:%S')
                new_entry += f"\n<h3>{time_str}</h3>\n\n"
                
                # 添加语音描述
                new_entry += f"<p>🎤 语音消息 ({duration}秒)</p>\n\n"
                
                # 添加语音链接HTML
                new_entry += f"{voice_html}\n\n"
                
                # 如果有ASR且识别成功，添加识别提示
                if self.asr_client:
                    new_entry += f"<p>🔄 <em>正在识别中...</em></p>\n\n"
                
                # 更新笔记内容
                updated_content = current_content + new_entry
                self.trilium_client.update_note_content(note_id, updated_content)
                
                # 发送确认消息
                status_msg = f"✅ 语音已保存到日记\n🎤 附件ID: {attachment_id}\n⏱️ 时长: {duration}秒\n📁 格式: {file_format}"
                
                # 如果启用了ASR，添加识别提示
                if self.asr_client:
                    status_msg += "\n🔄 正在识别中..."
                    
                await update.message.reply_text(status_msg)
                logger.info(f"用户 {update.effective_user.id} 保存语音到日记，附件ID: {attachment_id}")
                
                # 启动异步语音识别（如果启用）
                if self.asr_client:
                    import shutil
                    # 复制音频文件用于识别（因为原文件会在finally中删除）
                    recognition_file_path = temp_file_path + ".recognition.ogg"
                    shutil.copy2(temp_file_path, recognition_file_path)
                    logger.debug(f"已复制音频文件用于识别: {temp_file_path} -> {recognition_file_path}")
                    
                    # 在后台线程中执行识别
                    recognition_thread = threading.Thread(
                        target=self._recognize_and_update,
                        args=(recognition_file_path, note_id, update.effective_chat.id, 
                              context.bot, self.application),
                        daemon=True
                    )
                    recognition_thread.start()
                    logger.info("✅ 异步识别任务已启动")
                
            except Exception as upload_error:
                logger.error(f"上传语音失败: {upload_error}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
                await update.message.reply_text(f"❌ 保存语音失败: {str(upload_error)}")
        
        except Exception as e:
            logger.error(f"处理语音消息失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            await update.message.reply_text("❌ 保存语音失败，请稍后重试")
        
        finally:
            # 清理临时文件（识别文件由后台线程清理）
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"临时文件已删除: {temp_file_path}")
                except Exception as file_error:
                    logger.warning(f"删除临时文件失败: {file_error}")


    async def handle_document_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文档消息"""
        temp_file_path = None
        try:
            document = update.message.document
            file = await context.bot.get_file(document.file_id)

            # 下载文件到临时文件
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
                await file.download_to_drive(temp_file_path)

            # 构建消息内容
            caption = update.message.caption or f"文档: {document.file_name}"
            hashtags = extract_hashtags(caption)

            # 获取日记笔记
            diary_note = self.trilium_client.get_or_create_diary_note()
            note_id = diary_note.get('noteId') if isinstance(diary_note, dict) else diary_note.note_id

            # 上传文档附件
            try:
                attachment_id, file_html = self.trilium_client.upload_attachment(temp_file_path, note_id)
                logger.info(f"文档上传成功: {attachment_id}")

                # 获取当前笔记内容
                current_content = self.trilium_client.get_note_content(note_id)
                current_time = datetime.now()
                
                # 构建时间层次
                new_entry = self.build_time_hierarchy(current_content, current_time)
                
                # 添加具体时间和内容 (H3)
                time_str = current_time.strftime('%H:%M:%S')
                new_entry += f"\n<h3>{time_str}</h3>\n\n"
                
                # 添加文档描述
                new_entry += f"<p>📄 文档: {document.file_name}</p>\n\n"
                
                # 添加文件链接HTML
                new_entry += f"{file_html}\n\n"
                
                # 如果有标签，添加到消息中
                if hashtags:
                    tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                    new_entry += f"<p><strong>标签:</strong> {tags_html}</p>\n"
                
                # 更新笔记内容
                updated_content = current_content + new_entry
                self.trilium_client.update_note_content(note_id, updated_content)
                
                await update.message.reply_text(f"✅ 文档已保存到日记\n📎 附件ID: {attachment_id}")
                logger.info(f"用户 {update.effective_user.id} 保存文档到日记，附件ID: {attachment_id}")

            except Exception as upload_error:
                logger.error(f"上传文档失败: {upload_error}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
                await update.message.reply_text(f"❌ 保存文档失败: {str(upload_error)}")

        except Exception as e:
            logger.error(f"处理文档消息失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            await update.message.reply_text("❌ 保存文档失败，请稍后重试")
        
        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"临时文件已删除: {temp_file_path}")
                except Exception as file_error:
                    logger.warning(f"删除临时文件失败: {file_error}")



    def _recognize_and_update(self, audio_path: str, note_id: str, chat_id: int,
                             bot, application):
        """
        在后台线程中执行语音识别并更新Trilium
        
        Args:
            audio_path: 音频文件路径
            note_id: Trilium笔记ID
            chat_id: Telegram聊天ID
            bot: Telegram bot实例
            application: Application实例
        """
        try:
            logger.info(f"开始异步识别语音: {audio_path}")

            # 执行语音识别
            recognized_text = self.asr_client.recognize_file(audio_path, audio_format="ogg")

            if recognized_text:
                logger.info(f"识别成功: {recognized_text}")

                # 获取当前笔记内容
                current_content = self.trilium_client.get_note_content(note_id)

                # 在笔记末尾追加识别文本
                recognition_entry = f'\n<p><strong>🎤 识别文本：</strong>{recognized_text}</p>\n'
                updated_content = current_content + recognition_entry

                # 更新笔记内容
                self.trilium_client.update_note_content(note_id, updated_content)
                logger.info("✅ 识别结果已追加到Trilium笔记")

                # 尝试发送Telegram通知（非关键功能）
                try:
                    if self.event_loop and self.event_loop.is_running():
                        # 使用 asyncio.run_coroutine_threadsafe 从后台线程提交任务到主循环
                        message_text = f"🎤 识别完成：\n\n{recognized_text}"
                        future = asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id=chat_id,
                                text=message_text
                            ),
                            self.event_loop
                        )
                        logger.info("✅ 识别完成通知已提交到事件循环")
                        # 可选：等待结果（设置超时避免阻塞）
                        try:
                            future.result(timeout=5)
                            logger.debug("通知发送成功")
                        except Exception as timeout_error:
                            logger.debug(f"通知发送超时或失败: {timeout_error}")
                    else:
                        logger.debug("事件循环不可用，跳过Telegram通知")
                except Exception as send_error:
                    logger.warning(f"发送识别结果通知失败: {send_error}（非关键错误）")

            else:
                logger.warning("语音识别失败，未返回文本")

        except Exception as e:
            logger.error(f"异步识别失败: {e}", exc_info=True)
        finally:
            # 清理临时文件
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                    logger.debug(f"临时音频文件已删除: {audio_path}")
                except Exception as e:
                    logger.warning(f"删除临时音频文件失败: {e}")

    def setup_handlers(self, application: Application):
        """设置消息处理器"""
        # 命令处理器
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("today", self.today_command))
        application.add_handler(CommandHandler("search", self.search_command))
        application.add_handler(CommandHandler("recent", self.recent_command))
        application.add_handler(CommandHandler("status", self.status_command))

        # 消息处理器
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))  # 语音消息
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document_message))

    def run_bot(self):
        """运行Bot"""
        application = Application.builder().token(self.token).build()
        self.application = application  # 保存application引用供异步识别使用
        self.setup_handlers(application)

        logger.info("Telegram Bot 启动中...")
        logger.info("Bot 启动成功，开始监听消息...")
        
        # 保存事件循环引用（在启动后获取）
        self.event_loop = asyncio.get_event_loop()
        logger.debug(f"已保存事件循环引用: {self.event_loop}")
        
        application.run_polling()