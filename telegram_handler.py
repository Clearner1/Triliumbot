import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from datetime import datetime
import os
import tempfile
from config import Config
from trilium_client import TriliumClient
from utils import extract_hashtags, format_message_content

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    """Telegram Bot处理器"""

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.trilium_client = TriliumClient()
        self.allowed_users = []  # 可以在配置中添加允许的用户ID列表

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_message = """
🤖 欢迎使用 Trilium 日记 Bot！

我可以帮助你将 Telegram 消息保存到 Trilium 日记中。

支持的功能：
📝 文本消息 - 直接保存为日记内容
🖼️ 图片 - 保存图片并添加描述
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
• 图片（会自动上传）
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

            # 提取标签
            hashtags = extract_hashtags(message_text)

            # 格式化消息内容
            formatted_content, all_hashtags = format_message_content(message_text, hashtags)

            # 保存到Trilium
            self.trilium_client.append_message_to_diary(
                message_content=message_text,
                hashtags=all_hashtags
            )

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
                
                # 构建新的内容条目（包含描述文字和图片）
                current_time = datetime.now().strftime('%H:%M:%S')
                new_entry = f"\n\n<h2>{current_time}</h2>\n\n"
                
                # 添加图片描述
                if caption and caption != "图片":
                    new_entry += f"<p>{caption}</p>\n\n"
                
                # 添加图片HTML
                new_entry += f"{image_html}\n\n"
                
                # 如果有标签，添加到消息中
                if hashtags:
                    tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                    new_entry += f"<p><strong>标签:</strong> {tags_html}</p>"
                
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
                
                # 构建新的内容条目
                current_time = datetime.now().strftime('%H:%M:%S')
                new_entry = f"\n\n<h2>{current_time}</h2>\n\n"
                
                # 添加文档描述
                new_entry += f"<p>文档: {document.file_name}</p>\n\n"
                
                # 添加文件链接HTML
                new_entry += f"{file_html}\n\n"
                
                # 如果有标签，添加到消息中
                if hashtags:
                    tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                    new_entry += f"<p><strong>标签:</strong> {tags_html}</p>"
                
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
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document_message))

    def run_bot(self):
        """运行Bot"""
        application = Application.builder().token(self.token).build()
        self.setup_handlers(application)

        logger.info("Telegram Bot 启动中...")
        logger.info("Bot 启动成功，开始监听消息...")
        application.run_polling()