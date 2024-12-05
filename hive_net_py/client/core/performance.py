"""
HiveNet 客户端性能优化
"""
import asyncio
import logging
import time
import psutil
import weakref
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, TypeVar, Generic
from collections import deque

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class PerformanceMetrics:
    """性能指标"""
    message_throughput: float = 0.0  # 消息吞吐量（消息/秒）
    message_latency: float = 0.0     # 消息延迟（毫秒）
    memory_usage: float = 0.0        # 内存使用率（百分比）
    cpu_usage: float = 0.0           # CPU使用率（百分比）
    queue_size: int = 0              # 队列大小
    active_connections: int = 0       # 活跃连接数
    error_rate: float = 0.0          # 错误率（百分比）
    timestamp: float = field(default_factory=time.time)  # 指标时间戳

class ObjectPool(Generic[T]):
    """对象池"""
    
    def __init__(self, factory, initial_size: int = 10, max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self._pool: deque[T] = deque(maxlen=max_size)
        self._in_use: Set[T] = set()
        
        # 初始化对象池
        for _ in range(initial_size):
            self._pool.append(factory())
    
    def acquire(self) -> T:
        """获取对象"""
        try:
            obj = self._pool.popleft()
        except IndexError:
            if len(self._in_use) < self.max_size:
                obj = self.factory()
            else:
                raise RuntimeError("对象池已满")
        
        self._in_use.add(obj)
        return obj
    
    def release(self, obj: T):
        """释放对象"""
        if obj in self._in_use:
            self._in_use.remove(obj)
            if len(self._pool) < self.max_size:
                self._pool.append(obj)

class MessagePool:
    """消息对象池"""
    
    def __init__(self, initial_size: int = 100, max_size: int = 1000):
        from ...common.protocol import Message
        
        def message_factory():
            return Message(
                type=None,
                payload={},
                sequence=0,
                timestamp=0.0,
                source_id=""
            )
        
        self.pool = ObjectPool(message_factory, initial_size, max_size)
    
    def acquire(self):
        """获取消息对象"""
        return self.pool.acquire()
    
    def release(self, message):
        """释放消息对象"""
        # 重置消息对象状态
        message.type = None
        message.payload.clear()
        message.sequence = 0
        message.timestamp = 0.0
        message.source_id = ""
        message.target_id = None
        
        self.pool.release(message)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 1000
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None
        self._message_count = 0
        self._error_count = 0
        self._start_time = time.time()
        
        # 系统资源监控
        self._process = psutil.Process()
    
    def record_message(self):
        """记录消息"""
        self._message_count += 1
    
    def record_error(self):
        """记录错误"""
        self._error_count += 1
    
    async def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics())
        logger.info("性能监控已启动")
    
    async def stop(self):
        """停止监控"""
        if not self._running:
            return
        
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("性能监控已停止")
    
    async def _collect_metrics(self):
        """收集性能指标"""
        try:
            while self._running:
                # 计算消息吞吐量
                current_time = time.time()
                elapsed_time = current_time - self._start_time
                throughput = self._message_count / elapsed_time if elapsed_time > 0 else 0
                
                # 计算错误率
                total_operations = self._message_count + self._error_count
                error_rate = (self._error_count / total_operations * 100) if total_operations > 0 else 0
                
                # 收集系统资源使用情况
                metrics = PerformanceMetrics(
                    message_throughput=throughput,
                    message_latency=0.0,  # 需要实现延迟计算
                    memory_usage=self._process.memory_percent(),
                    cpu_usage=self._process.cpu_percent(),
                    queue_size=0,  # 需要从消息队列获取
                    active_connections=0,  # 需要从连接管理器获取
                    error_rate=error_rate,
                    timestamp=current_time
                )
                
                # 添加到历史记录
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history.pop(0)
                
                # 等待下一个收集周期
                await asyncio.sleep(self.collection_interval)
        except asyncio.CancelledError:
            logger.debug("性能指标收集已取消")
        except Exception as e:
            logger.error(f"性能指标收集出错: {e}")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        return self.metrics_history[-1] if self.metrics_history else PerformanceMetrics()
    
    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """获取性能指标历史"""
        return self.metrics_history.copy()
    
    def clear_history(self):
        """清除历史记录"""
        self.metrics_history.clear()
        self._message_count = 0
        self._error_count = 0
        self._start_time = time.time()

class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 0.1):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batch: List[Any] = []
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._processor = None
    
    def set_processor(self, processor):
        """设置处理器函数"""
        self._processor = processor
    
    async def start(self):
        """启动批处理器"""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("批处理器已启动")
    
    async def stop(self):
        """停止批处理器"""
        if not self._running:
            return
        
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            
            # 处理剩余的批次
            if self._batch:
                await self._process_batch(self._batch)
                self._batch.clear()
        logger.info("批处理器已停止")
    
    async def add_item(self, item: Any):
        """添加项目到批次"""
        self._batch.append(item)
        
        if len(self._batch) >= self.batch_size:
            batch = self._batch
            self._batch = []
            await self._process_batch(batch)
    
    async def _flush_loop(self):
        """刷新循环"""
        try:
            while self._running:
                await asyncio.sleep(self.flush_interval)
                
                if self._batch:
                    batch = self._batch
                    self._batch = []
                    await self._process_batch(batch)
        except asyncio.CancelledError:
            logger.debug("批处理刷新循环已取消")
        except Exception as e:
            logger.error(f"批处理刷新循环出错: {e}")
    
    async def _process_batch(self, batch: List[Any]):
        """处理批次"""
        if not self._processor:
            logger.warning("未设置批处理器")
            return
        
        try:
            await self._processor(batch)
        except Exception as e:
            logger.error(f"批处理出错: {e}")

class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._process = psutil.Process()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动资源监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("资源监控已启动")
    
    async def stop(self):
        """停止资源监控"""
        if not self._running:
            return
        
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("资源监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self._running:
                # 监控内存使用
                memory_percent = self._process.memory_percent()
                if memory_percent >= self.critical_threshold:
                    logger.critical(f"内存使用率达到临界值: {memory_percent:.1f}%")
                elif memory_percent >= self.warning_threshold:
                    logger.warning(f"内存使用率达到警告值: {memory_percent:.1f}%")
                
                # 监控CPU使用
                cpu_percent = self._process.cpu_percent()
                if cpu_percent >= self.critical_threshold:
                    logger.critical(f"CPU使用率达到临界值: {cpu_percent:.1f}%")
                elif cpu_percent >= self.warning_threshold:
                    logger.warning(f"CPU使用率达到警告值: {cpu_percent:.1f}%")
                
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.debug("资源监控循环已取消")
        except Exception as e:
            logger.error(f"资源监控循环出错: {e}")
    
    def get_resource_usage(self) -> Dict[str, float]:
        """获取资源使用情况"""
        return {
            'memory_percent': self._process.memory_percent(),
            'cpu_percent': self._process.cpu_percent(),
            'disk_usage': psutil.disk_usage('/').percent,
            'open_files': len(self._process.open_files()),
            'threads': self._process.num_threads()
        } 