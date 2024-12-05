"""
HiveNet 基础网络通信组件
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from ..protocol import Message, MessageType

logger = logging.getLogger(__name__)

class NetworkError(Exception):
    """网络错误基类"""
    pass

class ConnectionError(NetworkError):
    """连接错误"""
    pass

class MessageHandler:
    """消息处理器基类"""
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理接收到的消息"""
        method_name = f"handle_{message.type.name.lower()}"
        handler = getattr(self, method_name, self.handle_unknown)
        return await handler(message)
    
    async def handle_unknown(self, message: Message) -> Optional[Message]:
        """处理未知类型的消息"""
        logger.warning(f"收到未知类型的消息: {message.type}")
        return None

class NetworkConnection:
    """网络连接基类"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 handler: MessageHandler):
        self.reader = reader
        self.writer = writer
        self.handler = handler
        self._sequence = 0
        self.connected = True
    
    @property
    def sequence(self) -> int:
        """获取并递增序列号"""
        self._sequence += 1
        return self._sequence
    
    async def send_message(self, message: Message) -> None:
        """发送消息"""
        try:
            data = json.dumps(message.to_dict()).encode('utf-8') + b'\n'
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise NetworkError(f"发送消息失败: {e}")
    
    async def receive_message(self) -> Optional[Message]:
        """接收消息"""
        try:
            data = await self.reader.readline()
            if not data:
                self.connected = False
                return None
            
            message_dict = json.loads(data.decode('utf-8'))
            return Message.from_dict(message_dict)
        except Exception as e:
            logger.error(f"接收消息失败: {e}")
            raise NetworkError(f"接收消息失败: {e}")
    
    async def close(self) -> None:
        """关闭连接"""
        self.connected = False
        self.writer.close()
        await self.writer.wait_closed()
    
    async def start(self) -> None:
        """启动连接处理"""
        try:
            while self.connected:
                message = await self.receive_message()
                if message is None:
                    break
                
                response = await self.handler.handle_message(message)
                if response:
                    await self.send_message(response)
        except Exception as e:
            logger.error(f"连接处理错误: {e}")
        finally:
            await self.close() 