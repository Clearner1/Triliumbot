#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
豆包WebSocket流式语音识别客户端
使用流式输入模式 (bigmodel_nostream) 进行语音识别
"""

import json
import struct
import uuid
import logging
import websocket
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DoubaoASRClient:
    """豆包ASR WebSocket客户端"""
    
    # WebSocket地址 - 流式输入模式
    WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
    
    # 协议常量
    PROTOCOL_VERSION = 0b0001  # 版本1
    HEADER_SIZE = 0b0001       # 4字节
    
    # 消息类型
    MSG_TYPE_FULL_CLIENT_REQUEST = 0b0001
    MSG_TYPE_AUDIO_ONLY_REQUEST = 0b0010
    MSG_TYPE_FULL_SERVER_RESPONSE = 0b1001
    MSG_TYPE_ERROR_RESPONSE = 0b1111
    
    # 消息标志
    MSG_FLAG_NONE = 0b0000
    MSG_FLAG_POS_SEQUENCE = 0b0001
    MSG_FLAG_LAST_PACKET = 0b0010
    MSG_FLAG_NEG_SEQUENCE = 0b0011
    
    # 序列化方法
    SERIALIZATION_NONE = 0b0000
    SERIALIZATION_JSON = 0b0001
    
    # 压缩方法
    COMPRESSION_NONE = 0b0000
    COMPRESSION_GZIP = 0b0001
    
    def __init__(self, app_key: str, access_key: str):
        """
        初始化ASR客户端
        
        Args:
            app_key: 火山引擎APP ID
            access_key: 火山引擎Access Token
        """
        self.app_key = app_key
        self.access_key = access_key
        self.ws = None
        self.connect_id = str(uuid.uuid4())
        
    def recognize_file(self, audio_path: str, audio_format: str = "ogg") -> Optional[str]:
        """
        识别音频文件

        Args:
            audio_path: 音频文件路径
            audio_format: 音频格式 (ogg/mp3/wav)

        Returns:
            识别的文本，失败返回None
        """
        try:
            logger.info(f"开始识别音频: {audio_path}, 格式: {audio_format}")

            # 读取音频文件
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return None

            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            audio_size = len(audio_data)
            logger.info(f"音频文件大小: {audio_size} bytes")

            # 添加详细调试信息
            logger.info(f"音频参数: format={audio_format}, rate=16000, bits=16, channel=1")
            if audio_format == "ogg":
                logger.info("启用Opus编解码器")
            
            # 建立WebSocket连接
            if not self._connect():
                logger.error("WebSocket连接失败")
                return None
            
            # 发送full client request
            if not self._send_full_request(audio_format):
                logger.error("发送full client request失败")
                self._close()
                return None

            # 接收首个响应
            response = self._receive_response()
            if response is None:
                logger.error("接收首个响应失败")
                self._close()
                return None

            logger.info(f"收到首个响应: {response}")
            logger.info(f"首响应内容: audio_info={response.get('audio_info')}, result={response.get('result')}")
            
            # 分包发送音频数据
            chunk_size = 3200  # 约200ms的音频数据 (16000采样率*2字节*0.2秒)
            total_chunks = (audio_size + chunk_size - 1) // chunk_size
            logger.info(f"准备分包发送: 共{total_chunks}包, 每包{chunk_size}字节")
            
            final_text = ""  # 用于保存识别结果

            for i in range(total_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, audio_size)
                chunk = audio_data[start:end]

                is_last = (i == total_chunks - 1)

                logger.info(f"准备发送第{i+1}包, 起始位置:{start}, 结束位置:{end}, 大小:{len(chunk)}字节, 是否为最后包:{is_last}")

                if not self._send_audio_packet(chunk, is_last):
                    logger.error(f"发送音频包 {i+1}/{total_chunks} 失败")
                    self._close()
                    return None

                logger.info(f"已发送音频包 {i+1}/{total_chunks}")

                # 接收响应（流式输入模式下，每包发送后都可能返回结果）
                response = self._receive_response()
                if response:
                    logger.info(f"收到第{i+1}包响应: {response}")

                    # 如果收到结果且包含文本，保存下来
                    if 'result' in response:
                        text = response['result'].get('text', '')
                        if text:
                            final_text = text
                            logger.info(f"已收到识别结果: {text}")

                            # 如果是最后一个包，可以立即返回
                            if is_last:
                                logger.info("最后一包已收到结果，识别完成")
                                self._close()
                                return final_text
                else:
                    logger.debug(f"第{i+1}包未收到响应")

            # 如果循环结束还没返回，再尝试等待最终结果
            if not final_text:
                logger.info("所有包已发送，尝试获取最终结果...")
                max_retries = 5

                for i in range(max_retries):
                    logger.debug(f"第{i+1}次尝试接收最终响应...")
                    final_response = self._receive_response()

                    if final_response and 'result' in final_response:
                        text = final_response['result'].get('text', '')
                        if text:
                            final_text = text
                            logger.info(f"识别成功: {text}")
                            break
                        else:
                            logger.debug(f"第{i+1}次接收，无文本内容")
                    elif final_response is None:
                        logger.warning(f"第{i+1}次接收，响应为None，连接可能已关闭")
                        break
                    else:
                        logger.debug(f"第{i+1}次接收，响应: {final_response}")

            self._close()

            if final_text:
                return final_text
            else:
                logger.error(f"未获取到识别结果，已尝试{max_retries}次")
                logger.error(f"最后收到的响应: {final_response}")
                return None
                
        except Exception as e:
            logger.error(f"识别音频失败: {e}", exc_info=True)
            self._close()
            return None
        finally:
            logger.info("recognize_file方法执行结束")
    
    def _connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            # 构造请求头
            headers = {
                "X-Api-App-Key": self.app_key,
                "X-Api-Access-Key": self.access_key,
                "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
                "X-Api-Connect-Id": self.connect_id,
            }
            
            logger.info(f"连接WebSocket: {self.WS_URL}")
            logger.debug(f"Connect-Id: {self.connect_id}")
            
            # 建立连接
            self.ws = websocket.create_connection(
                self.WS_URL,
                header=headers,
                timeout=30
            )
            
            logger.info("WebSocket连接成功")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}", exc_info=True)
            return False
    
    def _close(self):
        """关闭WebSocket连接"""
        if self.ws:
            try:
                self.ws.close()
                logger.debug("WebSocket连接已关闭")
            except:
                pass
            self.ws = None
    
    def _build_header(self, message_type: int, message_flags: int, 
                     serialization: int, compression: int) -> bytes:
        """
        构造4字节协议头
        
        Args:
            message_type: 消息类型
            message_flags: 消息标志
            serialization: 序列化方法
            compression: 压缩方法
            
        Returns:
            4字节header
        """
        byte0 = (self.PROTOCOL_VERSION << 4) | self.HEADER_SIZE
        byte1 = (message_type << 4) | message_flags
        byte2 = (serialization << 4) | compression
        byte3 = 0x00  # Reserved
        
        return struct.pack('BBBB', byte0, byte1, byte2, byte3)
    
    def _send_full_request(self, audio_format: str) -> bool:
        """
        发送full client request（首包）

        Args:
            audio_format: 音频格式

        Returns:
            是否发送成功
        """
        try:
            # 构造请求参数
            request_data = {
                "user": {
                    "uid": "telegram_bot_user"
                },
                "audio": {
                    "format": audio_format,
                    "rate": 16000,
                    "bits": 16,
                    "channel": 1
                },
                "request": {
                    "model_name": "bigmodel",
                    "enable_itn": True,
                    "enable_punc": True,
                    "show_utterances": False
                }
            }

            # OGG格式需要指定codec为opus
            if audio_format == "ogg":
                request_data["audio"]["codec"] = "opus"
                logger.info("OGG格式已指定Opus编解码器")

            # 序列化为JSON
            payload = json.dumps(request_data, ensure_ascii=False).encode('utf-8')

            # 构造header (无压缩)
            header = self._build_header(
                self.MSG_TYPE_FULL_CLIENT_REQUEST,
                self.MSG_FLAG_NONE,
                self.SERIALIZATION_JSON,
                self.COMPRESSION_NONE
            )

            # 构造完整消息: header + payload_size + payload
            payload_size = struct.pack('>I', len(payload))  # big-endian
            message = header + payload_size + payload

            logger.debug(f"发送full client request, payload大小: {len(payload)}, 请求参数: {request_data}")
            self.ws.send(message, websocket.ABNF.OPCODE_BINARY)

            return True
            
        except Exception as e:
            logger.error(f"发送full client request失败: {e}", exc_info=True)
            return False
    
    def _send_audio_packet(self, audio_data: bytes, is_last: bool = False) -> bool:
        """
        发送audio only request（音频包）

        Args:
            audio_data: 音频数据
            is_last: 是否是最后一包

        Returns:
            是否发送成功
        """
        try:
            # 构造header
            message_flags = self.MSG_FLAG_LAST_PACKET if is_last else self.MSG_FLAG_NONE

            header = self._build_header(
                self.MSG_TYPE_AUDIO_ONLY_REQUEST,
                message_flags,
                self.SERIALIZATION_NONE,
                self.COMPRESSION_NONE
            )

            # 构造完整消息: header + payload_size + payload
            payload_size = struct.pack('>I', len(audio_data))  # big-endian
            message = header + payload_size + audio_data

            logger.debug(f"准备发送音频包消息: header长度={len(header)}, payload大小={len(audio_data)}, 总消息长度={len(message)}")
            bytes_sent = self.ws.send(message, websocket.ABNF.OPCODE_BINARY)
            logger.info(f"音频包已发送: {bytes_sent}字节")

            return True
            
        except Exception as e:
            logger.error(f"发送音频包失败: {e}", exc_info=True)
            return False
    
    def _receive_response(self) -> Optional[Dict[Any, Any]]:
        """
        接收服务器响应
        
        Returns:
            解析后的响应数据，失败返回None
        """
        try:
            # 接收消息
            data = self.ws.recv()
            
            if not data or len(data) < 8:
                logger.warning("收到空响应或数据不完整")
                return None
            
            # 解析header (4字节)
            header = data[0:4]
            byte0, byte1, byte2, byte3 = struct.unpack('BBBB', header)
            
            message_type = (byte1 >> 4) & 0x0F
            
            # 检查是否是错误响应
            if message_type == self.MSG_TYPE_ERROR_RESPONSE:
                error_code = struct.unpack('>I', data[4:8])[0]
                error_size = struct.unpack('>I', data[8:12])[0]
                error_msg = data[12:12+error_size].decode('utf-8')
                logger.error(f"服务器返回错误: code={error_code}, msg={error_msg}")
                return None
            
            # 解析序列号 (4字节)
            sequence = struct.unpack('>I', data[4:8])[0]
            
            # 解析payload大小 (4字节)
            payload_size = struct.unpack('>I', data[8:12])[0]
            
            # 解析payload
            if len(data) >= 12 + payload_size:
                payload = data[12:12+payload_size]
                
                # JSON解析
                try:
                    result = json.loads(payload.decode('utf-8'))
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    return None
            else:
                logger.warning(f"数据不完整: 期望{payload_size}字节, 实际{len(data)-12}字节")
                return None
                
        except websocket.WebSocketTimeoutException:
            logger.warning("接收响应超时")
            return None
        except Exception as e:
            logger.error(f"接收响应失败: {e}", exc_info=True)
            return None

