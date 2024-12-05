"""
测试会话管理功能
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock

from hive_net_py.server.core.session import SessionManager, SessionState, SessionInfo
from hive_net_py.common.network import NetworkConnection

@pytest.fixture
def session_manager():
    """创建会话管理器实例"""
    return SessionManager()

@pytest.mark.asyncio
async def test_session_lifecycle(session_manager):
    """测试会话生命周期"""
    await session_manager.start()
    
    try:
        client_id = "test_client"
        
        # 测试创建会话
        session = await session_manager.create_session(client_id)
        assert session.client_id == client_id
        assert session.state == SessionState.CONNECTING
        assert session.connection is None
        
        # 测试重复创建会话
        with pytest.raises(ValueError):
            await session_manager.create_session(client_id)
        
        # 测试更新会话
        mock_connection = AsyncMock(spec=NetworkConnection)
        updated_session = await session_manager.update_session(
            client_id,
            connection=mock_connection,
            state=SessionState.CONNECTED
        )
        assert updated_session is not None
        assert updated_session.connection == mock_connection
        assert updated_session.state == SessionState.CONNECTED
        
        # 测试获取会话
        session = session_manager.get_session(client_id)
        assert session is not None
        assert session.client_id == client_id
        
        # 测试移除会话
        await session_manager.remove_session(client_id)
        assert session_manager.get_session(client_id) is None
        assert client_id not in session_manager.active_sessions
    finally:
        await session_manager.stop()

@pytest.mark.asyncio
async def test_session_cleanup(session_manager):
    """测试会话清理"""
    await session_manager.start()
    
    try:
        # 修改清理间隔和超时时间以便测试
        session_manager._cleanup_interval = 0.1
        session_manager._session_timeout = 0.2
        
        # 创建测试会话
        client_id = "test_client"
        await session_manager.create_session(client_id)
        
        # 等待会话过期
        await asyncio.sleep(0.3)
        
        # 验证会话已被清理
        assert session_manager.get_session(client_id) is None
        assert client_id not in session_manager.active_sessions
    finally:
        await session_manager.stop()

@pytest.mark.asyncio
async def test_active_sessions(session_manager):
    """测试活跃会话统计"""
    await session_manager.start()
    
    try:
        # 创建多个会话
        clients = ["client1", "client2", "client3"]
        for client_id in clients:
            await session_manager.create_session(client_id)
        
        # 设置不同的会话状态
        await session_manager.update_session("client1", state=SessionState.CONNECTED)
        await session_manager.update_session("client2", state=SessionState.AUTHENTICATED)
        await session_manager.update_session("client3", state=SessionState.DISCONNECTING)
        
        # 验证活跃会话数量
        active_sessions = session_manager.active_sessions
        assert len(active_sessions) == 2
        assert "client1" in active_sessions
        assert "client2" in active_sessions
        assert "client3" not in active_sessions
        
        # 验证总会话数
        assert session_manager.session_count == 3
    finally:
        await session_manager.stop() 