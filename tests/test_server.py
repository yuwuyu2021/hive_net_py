"""
测试服务器功能
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock

from hive_net_py.server.core.server import HiveServer, ServerMessageHandler
from hive_net_py.common.protocol import Message, MessageType
from hive_net_py.common.network import NetworkConnection
from hive_net_py.server.core.session import SessionState

@pytest.fixture
def server():
    """创建服务器实例"""
    return HiveServer('127.0.0.1', 8888)

@pytest.mark.asyncio
async def test_server_start_stop(server):
    """测试服务器启动和停止"""
    # 模拟服务器启动
    mock_server = AsyncMock()
    server.server = mock_server
    
    await server.start(test_mode=True)
    assert server.is_running
    assert server.host == '127.0.0.1'
    assert server.port == 8888
    
    await server.stop()
    assert not server.is_running
    mock_server.close.assert_called_once()
    mock_server.wait_closed.assert_called_once()

@pytest.mark.asyncio
async def test_message_handling():
    """测试消息处理"""
    server = HiveServer()
    await server.start(test_mode=True)
    
    try:
        handler = ServerMessageHandler(server)
        
        # 测试连接消息
        connect_msg = Message(
            type=MessageType.CONNECT,
            payload={"client_id": "test"},
            sequence=1,
            timestamp=time.time(),
            source_id="test_client"
        )
        
        response = await handler.handle_message(connect_msg)
        assert response is not None
        assert response.type == MessageType.CONNECT
        assert response.payload["status"] == "connected"
        assert response.target_id == "test_client"
        
        # 验证会话状态
        session = server.session_manager.get_session("test_client")
        assert session is not None
        assert session.state == SessionState.CONNECTED
        
        # 测试断开连接消息
        disconnect_msg = Message(
            type=MessageType.DISCONNECT,
            payload={},
            sequence=2,
            timestamp=time.time(),
            source_id="test_client"
        )
        
        response = await handler.handle_message(disconnect_msg)
        assert response is not None
        assert response.type == MessageType.DISCONNECT
        assert response.payload["status"] == "disconnected"
        assert server.session_manager.get_session("test_client") is None
    finally:
        await server.stop()

@pytest.mark.asyncio
async def test_message_forwarding(server):
    """测试消息转发"""
    await server.start(test_mode=True)
    
    try:
        # 创建模拟的网络连接
        mock_connection = AsyncMock(spec=NetworkConnection)
        
        # 注册两个客户端
        client1_id = "client1"
        client2_id = "client2"
        
        # 创建会话并设置连接
        await server.session_manager.create_session(client1_id)
        await server.session_manager.create_session(client2_id)
        await server.session_manager.update_session(
            client2_id,
            connection=mock_connection,
            state=SessionState.CONNECTED
        )
        
        # 测试定向消息转发
        message = Message(
            type=MessageType.DATA,
            payload={"data": "test"},
            sequence=1,
            timestamp=time.time(),
            source_id=client1_id,
            target_id=client2_id
        )
        
        await server.forward_message(message)
        mock_connection.send_message.assert_called_once_with(message)
        
        # 测试广播消息
        await server.broadcast_message(message)
        assert mock_connection.send_message.call_count == 2
    finally:
        await server.stop()