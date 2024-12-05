"""
HiveNet 客户端核心模块
"""
import asyncio
import logging
from typing import Optional, Any
from ...common.config.base import ConnectionConfig

logger = logging.getLogger(__name__)

class HiveClient:
    """HiveNet客户端类"""
    
    def __init__(self, config: ConnectionConfig):
        """初始化客户端
        
        Args:
            config: 连接配置
        """
        self.config = config
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.retry_count = 0
    
    async def connect(self) -> bool:
        """连接到服务器
        
        Returns:
            连接是否成功
        """
        while self.retry_count < self.config.retry_count:
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    self.config.host,
                    self.config.port
                )
                self.connected = True
                self.retry_count = 0
                logger.info(f"已连接到服务器 {self.config.host}:{self.config.port}")
                return True
                
            except Exception as e:
                self.retry_count += 1
                logger.error(f"连接服务器失败 ({self.retry_count}/{self.config.retry_count}): {e}")
                if self.retry_count < self.config.retry_count:
                    await asyncio.sleep(self.config.retry_delay)
        
        return False
    
    async def disconnect(self):
        """断开连接"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
            finally:
                self.writer = None
                self.reader = None
                self.connected = False
    
    async def send(self, data: Any):
        """发送数据
        
        Args:
            data: 要发送的数据
        """
        if not self.connected:
            raise ConnectionError("未连接到服务器")
        
        try:
            # 将数据转换为字节
            if isinstance(data, str):
                data = data.encode()
            elif not isinstance(data, bytes):
                data = str(data).encode()
            
            # 发送数据
            self.writer.write(data)
            await self.writer.drain()
            
        except Exception as e:
            logger.error(f"发送数据时出错: {e}")
            raise
    
    async def receive(self, size: int = None) -> bytes:
        """接收数据
        
        Args:
            size: 要接收的字节数，如果为None则使用配置的缓冲区大小
            
        Returns:
            接收到的数据
        """
        if not self.connected:
            raise ConnectionError("未连接到服务器")
        
        try:
            # 接收数据
            data = await self.reader.read(size or self.config.buffer_size)
            if not data:
                raise ConnectionError("服务器已关闭连接")
            return data
            
        except Exception as e:
            logger.error(f"接收数据时出错: {e}")
            raise
    
    async def receive_until(self, separator: bytes = b'\n') -> bytes:
        """接收数据直到遇到分隔符
        
        Args:
            separator: 分隔符
            
        Returns:
            接收到的数据
        """
        if not self.connected:
            raise ConnectionError("未连接到服务器")
        
        try:
            # 接收数据
            data = await self.reader.readuntil(separator)
            return data
            
        except Exception as e:
            logger.error(f"接收数据时出错: {e}")
            raise
    
    async def receive_exactly(self, size: int) -> bytes:
        """接收指定字节数的数据
        
        Args:
            size: 要接收的字节数
            
        Returns:
            接收到的数据
        """
        if not self.connected:
            raise ConnectionError("未连接到服务器")
        
        try:
            # 接收数据
            data = await self.reader.readexactly(size)
            return data
            
        except Exception as e:
            logger.error(f"接收数据时出错: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """是否已连接
        
        Returns:
            是否已连接
        """
        return self.connected