import requests
import json
import os
from datetime import datetime
from config import Config
import logging
from utils import format_diary_title, format_diary_date, get_local_time

logger = logging.getLogger(__name__)

class TriliumClient:
    """Trilium ETAPI 客户端"""

    def __init__(self):
        self.api_token = Config.TRILIUM_API_TOKEN
        self.server_url = Config.TRILIUM_SERVER_URL.rstrip('/')
        self.parent_note_id = Config.DIARY_PARENT_NOTE_ID
        self.headers = {
            'Authorization': f'{self.api_token}',
            'Content-Type': 'application/json'
        }
        self._test_connection()

    def _test_connection(self):
        """测试连接"""
        try:
            response = self._make_request('GET', '/app-info')
            if response:
                logger.info("成功连接到Trilium服务器")
                return True
        except Exception as e:
            logger.error(f"连接Trilium服务器失败: {e}")
            raise

    def _make_request(self, method, endpoint, data=None, params=None):
        """发送HTTP请求"""
        url = f"{self.server_url}/etapi{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, data=json.dumps(data, ensure_ascii=False) if data else None, params=params)
            elif method == 'PUT':
                # 对于PUT请求（特别是内容更新），需要特殊处理UTF-8编码
                headers = self.headers.copy()
                headers['Content-Type'] = 'text/plain; charset=utf-8'
                response = requests.put(url, headers=headers, data=data.encode('utf-8') if data else None, params=params)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, data=json.dumps(data, ensure_ascii=False) if data else None, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()

            if response.content:
                # 尝试解析JSON，如果失败则返回原始文本
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return response.text
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应内容: {e.response.text}")
            raise

    def get_diary_note(self, date=None):
        """获取指定日期的日记笔记（使用Trilium原生日记API）"""
        if date is None:
            date = get_local_time()

        diary_date = format_diary_date(date)

        try:
            # 使用Trilium的原生日记API
            # 如果日记不存在，会自动创建
            url = f"/calendar/days/{diary_date}"
            response = self._make_request('GET', url)

            if response:
                logger.info(f"获取到日记笔记: {diary_date}")
                return response

            logger.error(f"无法获取日记笔记: {diary_date}")
            return None

        except Exception as e:
            logger.error(f"获取日记笔记失败: {e}")
            return None

    def get_or_create_diary_note(self, date=None):
        """获取或创建日记笔记（使用Trilium原生日记API）"""
        return self.get_diary_note(date)

    def _add_label(self, note_id, name, value):
        """添加标签到笔记"""
        try:
            label_data = {
                'noteId': note_id,
                'type': 'label',
                'name': name,
                'value': value
            }
            self._make_request('POST', '/attributes', label_data)
        except Exception as e:
            logger.warning(f"添加标签失败: {e}")

    def append_message_to_diary(self, message_content, hashtags=None, date=None):
        """将消息追加到日记笔记中"""
        try:
            # 获取日记笔记（使用原生日记API）
            diary_note = self.get_or_create_diary_note(date)
            if not diary_note:
                raise Exception("无法获取日记笔记")

            # 获取现有内容
            current_content = self.get_note_content(diary_note['noteId'])

            # 获取日期用于日志
            diary_date = format_diary_date(date) if date else format_diary_date()

            # 格式化新消息（使用HTML格式，更适合Trilium日记）
            current_time = get_local_time().strftime('%H:%M:%S')

            # 简化处理，直接使用原内容（不再转换链接）
            html_content = message_content

            new_entry = f"\n\n<h2>{current_time}</h2>\n\n<p>{html_content}</p>"

            # 如果有标签，添加到消息中
            if hashtags:
                tags_html = ", ".join([f"<span class='label'>#{tag}</span>" for tag in hashtags])
                new_entry += f"\n\n<p><strong>标签:</strong> {tags_html}</p>"

            # 追加新内容
            updated_content = current_content + new_entry
            self.update_note_content(diary_note['noteId'], updated_content)

            logger.info(f"成功追加消息到Trilium日记: {diary_date}")
            return diary_note

        except Exception as e:
            logger.error(f"追加消息到日记失败: {e}")
            raise

    def upload_attachment(self, file_path, note_id):
        """上传附件到指定笔记（一步上传，包含base64内容）
        
        Args:
            file_path: 文件路径
            note_id: 笔记ID
            
        Returns:
            tuple: (attachment_id, html_content) - 附件ID和HTML内容
        """
        try:
            import mimetypes
            import base64
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            filename = os.path.basename(file_path)

            # 读取文件并转换为base64
            with open(file_path, 'rb') as f:
                file_data = f.read()
                content_base64 = base64.b64encode(file_data).decode('utf-8')
            
            file_size = len(file_data)
            logger.info(f"准备上传文件: {filename}, MIME: {mime_type}, 大小: {file_size} bytes, Base64长度: {len(content_base64)}")

            # 对于图片，使用image角色（两步上传：先创建，再上传二进制内容）
            if mime_type.startswith('image/'):
                # 步骤1: 创建图片附件记录（不包含content）
                attachment_data = {
                    'ownerId': note_id,
                    'role': 'image',
                    'mime': mime_type,
                    'title': filename,
                    # 注意：不包含content字段
                    'position': 10
                }

                logger.info(f"步骤1: 正在创建图片附件记录...")
                
                try:
                    attachment = self._make_request('POST', '/attachments', attachment_data)
                except Exception as api_error:
                    logger.error(f"API请求失败，错误详情: {api_error}")
                    if hasattr(api_error, 'response') and api_error.response is not None:
                        logger.error(f"HTTP状态码: {api_error.response.status_code}")
                        logger.error(f"响应体: {api_error.response.text[:500]}")
                    raise
                
                if not attachment:
                    raise Exception("创建图片附件记录失败")

                attachment_id = attachment.get('attachmentId')
                if not attachment_id:
                    logger.error(f"返回的attachment对象: {attachment}")
                    raise Exception("attachment响应中没有attachmentId")
                
                logger.info(f"✅ 步骤1完成: 创建附件记录 {attachment_id}")
                
                # 步骤2: 上传原始二进制内容
                logger.info(f"步骤2: 正在上传图片二进制内容...")
                content_url = f"{self.server_url}/etapi/attachments/{attachment_id}/content"
                
                # 尝试不同的Content-Type
                upload_headers = {
                    'Authorization': self.api_token,
                    'Content-Type': 'application/octet-stream'  # 使用通用二进制类型
                }
                
                try:
                    response = requests.put(content_url, headers=upload_headers, data=file_data)
                    response.raise_for_status()
                    logger.info(f"✅ 步骤2完成: 成功上传图片内容，大小: {file_size} bytes")
                except Exception as upload_error:
                    logger.error(f"❌ 步骤2失败: 上传图片内容失败")
                    logger.error(f"错误: {upload_error}")
                    if hasattr(upload_error, 'response') and upload_error.response is not None:
                        logger.error(f"HTTP状态码: {upload_error.response.status_code}")
                        logger.error(f"响应体: {upload_error.response.text}")
                    raise
                
                # 验证上传结果
                try:
                    verify_url = f"{self.server_url}/etapi/attachments/{attachment_id}"
                    verify_headers = {'Authorization': self.api_token}
                    verify_response = requests.get(verify_url, headers=verify_headers)
                    verify_response.raise_for_status()
                    attachment_info = verify_response.json()
                    logger.info(f"🔍 验证attachment信息: {attachment_info}")
                    
                    content_length = attachment_info.get('contentLength', 0)
                    logger.info(f"📏 最终内容长度: {content_length} bytes (原始文件: {file_size} bytes)")
                    
                    if content_length == file_size:
                        logger.info(f"✅ 验证成功：内容长度匹配！")
                    else:
                        logger.warning(f"⚠️ 警告：内容长度不匹配！可能上传有问题")
                    
                except Exception as verify_error:
                    logger.warning(f"⚠️ 验证失败: {verify_error}")

                # 生成图片的HTML代码
                image_html = f'<figure class="image"><img src="api/attachments/{attachment_id}/image/{filename}" alt="{filename}"></figure>'
                
                logger.info(f"📝 生成的图片HTML: {image_html}")
                logger.info(f"🔗 图片访问路径: {self.server_url}/api/attachments/{attachment_id}/image/{filename}")

                return (attachment_id, image_html)
                
            else:
                # 对于非图片文件，创建普通的附件
                attachment_data = {
                    'ownerId': note_id,
                    'role': 'attachment',
                    'mime': mime_type,
                    'title': filename,
                    'content': content_base64,
                    'position': 10
                }

                logger.info(f"正在创建文件附件...")
                attachment = self._make_request('POST', '/attachments', attachment_data)
                if not attachment:
                    raise Exception("创建文件附件失败")
                    
                attachment_id = attachment.get('attachmentId')
                logger.info(f"✅ 成功创建文件附件: {attachment_id}, 文件: {filename}")
                
                # 生成文件链接的HTML
                file_html = f'<p><a href="api/attachments/{attachment_id}/download">{filename}</a></p>'
                
                return (attachment_id, file_html)

        except Exception as e:
            logger.error(f"❌ 上传附件失败: {e}")
            import traceback
            logger.error(f"完整错误堆栈: {traceback.format_exc()}")
            raise

    def get_attachment_html(self, attachment_id, file_path):
        """获取附件的HTML表示"""
        try:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)

            if mime_type and mime_type.startswith('image/'):
                # 对于图片，生成正确的HTML
                filename = os.path.basename(file_path)
                html = f'<figure class="image"><img src="api/attachments/{attachment_id}/image/{filename}" alt="{filename}"></figure>'
                return html
            else:
                # 对于其他文件，生成链接
                filename = os.path.basename(file_path)
                html = f'<p><a href="api/attachments/{attachment_id}/file/{filename}">{filename}</a></p>'
                return html

        except Exception as e:
            logger.error(f"生成附件HTML失败: {e}")
            return f'<p>附件: {os.path.basename(file_path)}</p>'

    def get_note_content(self, note_id):
        """获取笔记内容"""
        try:
            url = f"/notes/{note_id}/content"
            response = self._make_request('GET', url)
            return response if response else ""
        except Exception as e:
            logger.error(f"获取笔记内容失败: {e}")
            return ""

    def update_note_content(self, note_id, content):
        """更新笔记内容"""
        try:
            url = f"/notes/{note_id}/content"
            self._make_request('PUT', url, content)
        except Exception as e:
            logger.error(f"更新笔记内容失败: {e}")
            raise

    def get_diary_content(self, date=None):
        """获取指定日期的日记内容"""
        note = self.find_diary_note(date)
        if note:
            return self.get_note_content(note['noteId'])
        return None

    def search_in_diaries(self, keyword, limit=10):
        """在所有日记中搜索关键词"""
        try:
            # 搜索包含diary标签的笔记和关键词
            search_query = f'#diary {keyword}'
            search_params = {
                'search': search_query,
                'limit': limit
            }

            response = self._make_request('GET', '/notes', params=search_params)
            results = []

            if response and 'results' in response:
                for note in response['results']:
                    results.append({
                        'title': note['title'],
                        'date': self._get_note_date_attribute(note),
                        'content': self.get_note_content(note['noteId']),
                        'note_id': note['noteId']
                    })

            return results

        except Exception as e:
            logger.error(f"搜索日记失败: {e}")
            return []

    def _get_note_date_attribute(self, note):
        """从笔记中获取日期属性"""
        if 'attributes' in note:
            for attr in note['attributes']:
                if attr['type'] == 'label' and attr['name'] == 'date':
                    return attr['value']
        return None

    def get_recent_diaries(self, days=7):
        """获取最近几天的日记列表"""
        try:
            # 搜索包含diary标签的笔记
            search_params = {
                'search': '#diary',
                'orderBy': 'dateModified',
                'orderDirection': 'desc',
                'limit': days
            }

            response = self._make_request('GET', '/notes', params=search_params)
            diaries = []

            if response and 'results' in response:
                for note in response['results']:
                    diaries.append({
                        'title': note['title'],
                        'date': self._get_note_date_attribute(note),
                        'note_id': note['noteId']
                    })

            return diaries

        except Exception as e:
            logger.error(f"获取最近日记失败: {e}")
            return []