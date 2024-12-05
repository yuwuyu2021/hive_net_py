"""
HiveNet 服务器会话管理
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum, auto

from ...common.network import NetworkConnection

logger = logging.getLogger(__name__)

class SessionState(Enum):
    """会话状态"""
    CONNECTING = auto()    # 正在连接
    CONNECTED = auto()     # 已连接
    AUTHENTICATING = auto()# 正在认证
    AUTHENTICATED = auto() # 已认证
    DISCONNECTING = auto() # 正在断开
    DISCONNECTED = auto()  # 已断开
    AUTH_FAILED = auto()   # 认证失败

@dataclass
class AuthInfo:
    """认证信息"""
    username: str
    token: str
    auth_time: float
    expire_time: float
    permissions: list[str] = None

@dataclass
class SessionInfo:
    """会话信息"""
    client_id: str
    connection: Optional[NetworkConnection]
    state: SessionState
    created_at: float
    last_active_at: float
    auth_info: Optional[AuthInfo] = None
    failed_auth_attempts: int = 0
    last_auth_attempt: float = 0

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 60  # 清理间隔（秒）
        self._session_timeout = 300  # 会话超时时间（秒）
        self._max_auth_attempts = 3  # 最大认证尝试次数
        self._auth_timeout = 300     # 认证超时时间（秒）
        self._auth_cooldown = 60     # 认证失败冷却时间（秒）
        self._max_sessions = 1000    # 最大会话数
        self._stats = {
            "total_sessions": 0,
            "auth_success": 0,
            "auth_failed": 0
        }
    
    async def start(self):
        """启动会话管理器"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("会话管理器已启动")
    
    async def stop(self):
        """停止会话管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("会话管理器已停止")
    
    async def create_session(self, client_id: str) -> SessionInfo:
        """创建新会话"""
        if len(self.sessions) >= self._max_sessions:
            raise ValueError("已达到最大会话数限制")
            
        if client_id in self.sessions:
            raise ValueError(f"客户端 {client_id} 已存在会话")
        
        now = time.time()
        session = SessionInfo(
            client_id=client_id,
            connection=None,
            state=SessionState.CONNECTING,
            created_at=now,
            last_active_at=now
        )
        self.sessions[client_id] = session
        self._stats["total_sessions"] += 1
        logger.info(f"已为客户端 {client_id} 创建会话")
        return session
    
    def get_session(self, client_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        return self.sessions.get(client_id)
    
    async def update_session(self, client_id: str, 
                           connection: Optional[NetworkConnection] = None,
                           state: Optional[SessionState] = None,
                           auth_info: Optional[Dict] = None) -> Optional[SessionInfo]:
        """更新会话信息"""
        session = self.sessions.get(client_id)
        if not session:
            logger.warning(f"客户端 {client_id} 的会话不存在")
            return None
        
        if connection is not None:
            session.connection = connection
        if state is not None:
            session.state = state
        if auth_info is not None:
            session.auth_info = auth_info
        
        session.last_active_at = time.time()
        return session
    
    async def remove_session(self, client_id: str):
        """移除会话"""
        if client_id in self.sessions:
            session = self.sessions[client_id]
            if session.connection:
                await session.connection.close()
            del self.sessions[client_id]
            logger.info(f"已移除客户端 {client_id} 的会话")
    
    async def _cleanup_loop(self):
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理会话时出错: {e}")
    
    async def _cleanup_expired_sessions(self):
        """清理过期的会话"""
        now = time.time()
        expired_clients = []
        
        for client_id, session in self.sessions.items():
            # 检查会话超时
            if now - session.last_active_at > self._session_timeout:
                expired_clients.append(client_id)
                continue
                
            # 检查认证超时
            if (session.state == SessionState.AUTHENTICATED and 
                session.auth_info and now > session.auth_info.expire_time):
                session.state = SessionState.CONNECTED
                session.auth_info = None
                logger.info(f"客户端 {client_id} 认证已过期")
        
        for client_id in expired_clients:
            logger.info(f"清理过期会话: {client_id}")
            await self.remove_session(client_id)
    
    @property
    def active_sessions(self) -> Set[str]:
        """获取活跃会话列表"""
        return {
            client_id for client_id, session in self.sessions.items()
            if session.state in (SessionState.CONNECTED, SessionState.AUTHENTICATED)
        }
    
    @property
    def session_count(self) -> int:
        """获取会话总数"""
        return len(self.sessions) 
    
    async def authenticate_session(self, client_id: str, auth_data: dict) -> bool:
        """认证会话
        
        Args:
            client_id: 客户端ID
            auth_data: 认证数据，包含username和token
            
        Returns:
            bool: 认证是否成功
        """
        session = self.sessions.get(client_id)
        if not session:
            logger.warning(f"客户端 {client_id} 的会话不存在")
            return False
            
        now = time.time()
        
        # 检查认证尝试次数和冷却时间
        if (session.failed_auth_attempts >= self._max_auth_attempts and 
            now - session.last_auth_attempt < self._auth_cooldown):
            logger.warning(f"客户端 {client_id} 认证尝试次数过多，请稍后再试")
            return False
            
        session.last_auth_attempt = now
        
        try:
            # TODO: 实现实际的认证逻辑
            username = auth_data.get("username")
            token = auth_data.get("token")
            
            if not username or not token:
                raise ValueError("缺少认证信息")
                
            # 这里应该调用实际的认证服务
            # 目前使用模拟的认证逻辑
            if username == "admin" and token == "test_token":
                auth_info = AuthInfo(
                    username=username,
                    token=token,
                    auth_time=now,
                    expire_time=now + self._auth_timeout,
                    permissions=["admin"]
                )
                
                session.auth_info = auth_info
                session.state = SessionState.AUTHENTICATED
                session.failed_auth_attempts = 0
                self._stats["auth_success"] += 1
                logger.info(f"客户端 {client_id} 认证成功")
                return True
            
            session.failed_auth_attempts += 1
            session.state = SessionState.AUTH_FAILED
            self._stats["auth_failed"] += 1
            logger.warning(f"客户端 {client_id} 认证失败")
            return False
            
        except Exception as e:
            logger.error(f"认证过程出错: {e}")
            session.failed_auth_attempts += 1
            session.state = SessionState.AUTH_FAILED
            self._stats["auth_failed"] += 1
            return False
    
    def get_session_stats(self) -> dict:
        """获取会话统计信息"""
        active_count = len(self.active_sessions)
        authenticated_count = len([s for s in self.sessions.values() 
                                 if s.state == SessionState.AUTHENTICATED])
        
        return {
            **self._stats,
            "active_sessions": active_count,
            "authenticated_sessions": authenticated_count,
            "current_sessions": len(self.sessions)
        }
    
    def check_session_permission(self, client_id: str, permission: str) -> bool:
        """检查会话权限
        
        Args:
            client_id: 客户端ID
            permission: 权限名称
            
        Returns:
            bool: 是否有权限
        """
        session = self.sessions.get(client_id)
        if not session or session.state != SessionState.AUTHENTICATED:
            return False
            
        return (session.auth_info and 
                session.auth_info.permissions and 
                permission in session.auth_info.permissions)