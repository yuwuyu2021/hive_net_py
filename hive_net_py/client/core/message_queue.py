"""
HiveNet 客户端消息队列
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from ...common.protocol import Message, MessageType

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    """队列优先级"""
    HIGH = auto()    # 高优先级
    NORMAL = auto()  # 普通优先级
    LOW = auto()     # 低优先级

@dataclass
class QueueConfig:
    """队列配置"""
    max_size: int = 1000  # 最大队列大小
    batch_size: int = 10  # 批处理大小
    flush_interval: float = 0.1  # 刷新间隔（秒）

@dataclass
class QueueStats:
    """队列统计信息"""
    total_enqueued: int = 0  # 总入队消息数
    total_dequeued: int = 0  # 总出队消息数
    total_dropped: int = 0   # 总丢弃消息数
    queue_size: int = 0      # 当前队列大小

class MessageQueue:
    """消息队列"""
    
    def __init__(self, config: Optional[QueueConfig] = None):
        self.config = config or QueueConfig()
        self.stats = QueueStats()
        self._queues: Dict[QueuePriority, asyncio.Queue] = {
            QueuePriority.HIGH: asyncio.Queue(maxsize=self.config.max_size),
            QueuePriority.NORMAL: asyncio.Queue(maxsize=self.config.max_size),
            QueuePriority.LOW: asyncio.Queue(maxsize=self.config.max_size)
        }
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动消息队列"""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("消息队列已启动")
    
    async def stop(self):
        """停止消息队列"""
        if not self._running:
            return
        
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        logger.info("消息队列已停止")
    
    async def put(self, message: Dict[str, Any], priority: QueuePriority = QueuePriority.NORMAL) -> bool:
        """将消息加入队列"""
        if not self._running:
            await self.start()  # 自动启动队列
        
        queue = self._queues[priority]
        try:
            if queue.qsize() >= self.config.max_size:
                logger.warning(f"队列已满，消息被丢弃: {message}")
                self.stats.total_dropped += 1
                return False
            
            await queue.put(message)
            self.stats.total_enqueued += 1
            self.stats.queue_size = sum(q.qsize() for q in self._queues.values())
            return True
        except asyncio.QueueFull:
            logger.warning(f"队列已满，消息被丢弃: {message}")
            self.stats.total_dropped += 1
            return False
    
    async def get(self) -> Optional[Dict[str, Any]]:
        """从队列中获取消息"""
        if not self._running:
            await self.start()  # 自动启动队列
        
        # 按优先级获取消息
        for priority in QueuePriority:
            queue = self._queues[priority]
            try:
                message = queue.get_nowait()
                queue.task_done()
                self.stats.total_dequeued += 1
                self.stats.queue_size = sum(q.qsize() for q in self._queues.values())
                return message
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    def is_closed(self) -> bool:
        """检查队列是否已关闭"""
        return not self._running
    
    async def _flush_loop(self):
        """消息刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                
                # 检查所有队列
                for priority in QueuePriority:
                    queue = self._queues[priority]
                    messages = []
                    
                    # 批量获取消息
                    for _ in range(self.config.batch_size):
                        try:
                            message = queue.get_nowait()
                            messages.append(message)
                            queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                    
                    # 更新统计信息
                    if messages:
                        self.stats.total_dequeued += len(messages)
                        self.stats.queue_size = sum(q.qsize() for q in self._queues.values())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"消息刷新出错: {e}")
                continue
    
    async def register_handler(self, message_type: MessageType, handler: asyncio.Future):
        """注册消息处理器"""
        if message_type not in self._handlers:
            self._handlers[message_type] = set()
        self._handlers[message_type].add(handler)
        logger.debug(f"注册消息处理器: {message_type}")
    
    async def unregister_handler(self, message_type: MessageType, handler: asyncio.Future):
        """注销消息处理器"""
        if message_type in self._handlers:
            self._handlers[message_type].discard(handler)
            if not self._handlers[message_type]:
                del self._handlers[message_type]
        logger.debug(f"注销消息处理器: {message_type}")
    
    async def _process_messages(self, messages: List[Dict[str, Any]]):
        """处理消息批次"""
        for message in messages:
            handlers = self._handlers.get(message.get("type", ""), set())
            if not handlers:
                logger.warning(f"没有找到消息处理器: {message.get('type', '')}")
                continue
            
            # 并发调用所有处理器
            tasks = [
                asyncio.create_task(handler(message))
                for handler in handlers
            ]
            
            try:
                await asyncio.gather(*tasks)
                self.stats.total_dequeued += 1
            except Exception as e:
                logger.error(f"处理消息时出错: {e}")
                # 继续处理其他消息 