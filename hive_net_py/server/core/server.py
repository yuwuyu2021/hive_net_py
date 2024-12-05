"""
HiveNet 服务器核心实现
"""
import asyncio
import logging
from typing import Dict, Optional, Set
import time

from ...common.network import MessageHandler, NetworkConnection
from ...common.protocol import Message, MessageType
from .session import SessionManager, SessionState

logger = logging.getLogger(__name__)

class ServerMessageHandler(MessageHandler):
    """服务器消息处理器"""
    
    def __init__(self, server: 'HiveServer'):
        self.server = server
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息"""
        handlers = {
            MessageType.CONNECT: self.handle_connect,
            MessageType.DISCONNECT: self.handle_disconnect,
            MessageType.AUTH: self.handle_auth,
            MessageType.DATA: self.handle_data
        }
        
        handler = handlers.get(message.type)
        if handler:
            return await handler(message)
        else:
            logger.warning(f"未知的消息类型: {message.type}")
            return None
    
    async def handle_connect(self, message: Message) -> Optional[Message]:
        """处理连接请求"""
        client_id = message.source_id
        try:
            session = await self.server.session_manager.create_session(client_id)
            await self.server.session_manager.update_session(
                client_id, 
                state=SessionState.CONNECTED
            )
            return Message(
                type=MessageType.CONNECT,
                payload={"status": "connected", "require_auth": True},
                sequence=message.sequence,
                timestamp=time.time(),
                source_id="server",
                target_id=client_id
            )
        except ValueError as e:
            logger.warning(f"连接请求失败: {e}")
            return Message(
                type=MessageType.ERROR,
                payload={"error": str(e)},
                sequence=message.sequence,
                timestamp=time.time(),
                source_id="server",
                target_id=client_id
            )
    
    async def handle_auth(self, message: Message) -> Optional[Message]:
        """处理认证请求"""
        client_id = message.source_id
        auth_data = message.payload
        
        success = await self.server.session_manager.authenticate_session(
            client_id, 
            auth_data
        )
        
        if success:
            return Message(
                type=MessageType.AUTH,
                payload={"status": "authenticated"},
                sequence=message.sequence,
                timestamp=time.time(),
                source_id="server",
                target_id=client_id
            )
        else:
            return Message(
                type=MessageType.ERROR,
                payload={
                    "error": "认证失败",
                    "code": "AUTH_FAILED"
                },
                sequence=message.sequence,
                timestamp=time.time(),
                source_id="server",
                target_id=client_id
            )
    
    async def handle_disconnect(self, message: Message) -> Optional[Message]:
        """处理断开连接请求"""
        client_id = message.source_id
        await self.server.session_manager.update_session(
            client_id, 
            state=SessionState.DISCONNECTING
        )
        await self.server.session_manager.remove_session(client_id)
        return Message(
            type=MessageType.DISCONNECT,
            payload={"status": "disconnected"},
            sequence=message.sequence,
            timestamp=time.time(),
            source_id="server",
            target_id=client_id
        )
    
    async def handle_data(self, message: Message) -> Optional[Message]:
        """处理数据消息"""
        client_id = message.source_id
        
        # 检查会话状态和权限
        session = self.server.session_manager.get_session(client_id)
        if not session or session.state != SessionState.AUTHENTICATED:
            return Message(
                type=MessageType.ERROR,
                payload={
                    "error": "未认证",
                    "code": "NOT_AUTHENTICATED"
                },
                sequence=message.sequence,
                timestamp=time.time(),
                source_id="server",
                target_id=client_id
            )
        
        # 检查特定权限（如果需要）
        if message.payload.get("require_permission"):
            permission = message.payload["require_permission"]
            if not self.server.session_manager.check_session_permission(
                client_id, 
                permission
            ):
                return Message(
                    type=MessageType.ERROR,
                    payload={
                        "error": "权限不足",
                        "code": "PERMISSION_DENIED"
                    },
                    sequence=message.sequence,
                    timestamp=time.time(),
                    source_id="server",
                    target_id=client_id
                )
        
        if message.target_id:
            # 转发给特定客户端
            await self.server.forward_message(message)
        else:
            # 广播给所有客户端
            await self.server.broadcast_message(message)
        return None

class HiveServer:
    """HiveNet 服务器"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        self.host = host
        self.port = port
        self.session_manager = SessionManager()
        self.server = None
        self._running = False
        self._serve_task = None
    
    async def start(self, test_mode: bool = False):
        """
        启动服务器
        
        Args:
            test_mode: 是否在测试模式下运行，如果是则不会进入serve_forever循环
        """
        try:
            await self.session_manager.start()
            if not test_mode:
                self.server = await asyncio.start_server(
                    self._handle_client,
                    self.host,
                    self.port
                )
            self._running = True
            logger.info(f"服务器启动于 {self.host}:{self.port}")
            
            if not test_mode and self.server:
                self._serve_task = asyncio.create_task(self._serve())
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            raise
    
    async def _serve(self):
        """服务器主循环"""
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """停止服务器"""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            if self._serve_task:
                self._serve_task.cancel()
                try:
                    await self._serve_task
                except asyncio.CancelledError:
                    pass
        await self.session_manager.stop()
        logger.info("服务器已停止")
    
    async def _handle_client(self, reader: asyncio.StreamReader, 
                           writer: asyncio.StreamWriter):
        """处理新的客户端连接"""
        handler = ServerMessageHandler(self)
        connection = NetworkConnection(reader, writer, handler)
        await connection.start()
    
    async def forward_message(self, message: Message):
        """转发消息给特定客户端"""
        if not message.target_id:
            logger.warning("消息没有指定目标客户端")
            return
        
        session = self.session_manager.get_session(message.target_id)
        if not session or not session.connection:
            logger.warning(f"目标客户端 {message.target_id} 不存在或未连接")
            return
        
        try:
            await session.connection.send_message(message)
        except Exception as e:
            logger.error(f"转发消息失败: {e}")
    
    async def broadcast_message(self, message: Message):
        """广播消息给所有客户端"""
        for client_id in self.session_manager.active_sessions:
            if client_id != message.source_id:
                session = self.session_manager.get_session(client_id)
                if session and session.connection:
                    try:
                        await session.connection.send_message(message)
                    except Exception as e:
                        logger.error(f"广播消息到客户端 {client_id} 失败: {e}")
    
    @property
    def is_running(self) -> bool:
        """服务器是否正在运行"""
        return self._running
    
    @property
    def client_count(self) -> int:
        """当前连接的客户端数量"""
        return self.session_manager.session_count 