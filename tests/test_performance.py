"""
测试性能优化功能
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch

from hive_net_py.client.core.performance import (
    ObjectPool,
    MessagePool,
    PerformanceMonitor,
    BatchProcessor,
    ResourceMonitor,
    PerformanceMetrics
)
from hive_net_py.common.protocol import Message, MessageType

@pytest.fixture
def object_pool():
    """创建对象池实例"""
    return ObjectPool(lambda: object(), initial_size=5, max_size=10)

@pytest.fixture
def message_pool():
    """创建消息池实例"""
    return MessagePool(initial_size=5, max_size=10)

@pytest.fixture
def performance_monitor():
    """创建性能监控器实例"""
    return PerformanceMonitor(collection_interval=0.1)

@pytest.fixture
def batch_processor():
    """创建批处理器实例"""
    return BatchProcessor(batch_size=5, flush_interval=0.1)

@pytest.fixture
def resource_monitor():
    """创建资源监控器实例"""
    return ResourceMonitor(warning_threshold=80.0, critical_threshold=90.0)

def test_object_pool_initialization(object_pool):
    """测试对象池初始化"""
    assert len(object_pool._pool) == 5
    assert len(object_pool._in_use) == 0
    assert object_pool.max_size == 10

def test_object_pool_acquire_release(object_pool):
    """测试对象池获取和释放"""
    # 获取对象
    obj1 = object_pool.acquire()
    assert len(object_pool._pool) == 4
    assert len(object_pool._in_use) == 1
    
    # 释放对象
    object_pool.release(obj1)
    assert len(object_pool._pool) == 5
    assert len(object_pool._in_use) == 0
    
    # 获取超过初始大小的对象
    objects = [object_pool.acquire() for _ in range(8)]
    assert len(object_pool._pool) == 0
    assert len(object_pool._in_use) == 8
    
    # 尝试获取超过最大大小的对象
    with pytest.raises(RuntimeError):
        for _ in range(3):
            object_pool.acquire()

def test_message_pool_operations(message_pool):
    """测试消息池操作"""
    # 获取消息对象
    message = message_pool.acquire()
    assert isinstance(message, Message)
    assert message.type is None
    assert not message.payload
    assert message.sequence == 0
    
    # 修改消息对象
    message.type = MessageType.DATA
    message.payload["test"] = "data"
    message.sequence = 1
    
    # 释放消息对象
    message_pool.release(message)
    assert message.type is None
    assert not message.payload
    assert message.sequence == 0

@pytest.mark.asyncio
async def test_performance_monitor():
    """测试性能监控器"""
    monitor = PerformanceMonitor(collection_interval=0.1)
    
    # 启动监控
    await monitor.start()
    
    try:
        # 记录一些消息和错误
        for _ in range(10):
            monitor.record_message()
        monitor.record_error()
        
        # 等待收集周期
        await asyncio.sleep(0.2)
        
        # 验证指标
        metrics = monitor.get_current_metrics()
        assert metrics.message_throughput > 0
        assert metrics.error_rate == 1 / 11 * 100  # 1个错误，总共11个操作
        assert len(monitor.get_metrics_history()) > 0
        
        # 清除历史记录
        monitor.clear_history()
        assert not monitor.metrics_history
        assert monitor._message_count == 0
        assert monitor._error_count == 0
    finally:
        await monitor.stop()

@pytest.mark.asyncio
async def test_batch_processor():
    """测试批处理器"""
    processor = BatchProcessor(batch_size=3, flush_interval=0.1)
    
    # 创建处理器函数
    processed_items = []
    async def process_batch(batch):
        processed_items.extend(batch)
    
    processor.set_processor(process_batch)
    
    # 启动处理器
    await processor.start()
    
    try:
        # 添加项目
        for i in range(5):
            await processor.add_item(i)
        
        # 等待处理完成
        await asyncio.sleep(0.2)
        
        # 验证处理结果
        assert len(processed_items) == 5
        assert processed_items == [0, 1, 2, 3, 4]
    finally:
        await processor.stop()

@pytest.mark.asyncio
async def test_resource_monitor():
    """测试资源监控器"""
    monitor = ResourceMonitor(warning_threshold=0.0, critical_threshold=100.0)
    
    # 启动监控
    await monitor.start()
    
    try:
        # 等待监控周期
        await asyncio.sleep(0.2)
        
        # 获取资源使用情况
        usage = monitor.get_resource_usage()
        assert 'memory_percent' in usage
        assert 'cpu_percent' in usage
        assert 'disk_usage' in usage
        assert 'open_files' in usage
        assert 'threads' in usage
    finally:
        await monitor.stop()

@pytest.mark.asyncio
async def test_performance_integration():
    """测试性能优化组件集成"""
    # 创建组件实例
    message_pool = MessagePool(initial_size=5, max_size=10)
    performance_monitor = PerformanceMonitor(collection_interval=0.1)
    batch_processor = BatchProcessor(batch_size=3, flush_interval=0.1)
    resource_monitor = ResourceMonitor()
    
    # 创建批处理器函数
    processed_messages = []
    async def process_batch(batch):
        processed_messages.extend(batch)
        performance_monitor.record_message()
    
    batch_processor.set_processor(process_batch)
    
    # 启动所有组件
    await asyncio.gather(
        performance_monitor.start(),
        batch_processor.start(),
        resource_monitor.start()
    )
    
    try:
        # 模拟消息处理
        for _ in range(5):
            message = message_pool.acquire()
            message.type = MessageType.DATA
            message.payload["test"] = "data"
            await batch_processor.add_item(message)
        
        # 等待处理完成
        await asyncio.sleep(0.3)
        
        # 验证结果
        assert len(processed_messages) == 5
        metrics = performance_monitor.get_current_metrics()
        assert metrics.message_throughput > 0
        
        # 验证资源监控
        usage = resource_monitor.get_resource_usage()
        assert all(key in usage for key in [
            'memory_percent', 'cpu_percent', 'disk_usage', 'open_files', 'threads'
        ])
    finally:
        # 停止所有组件
        await asyncio.gather(
            performance_monitor.stop(),
            batch_processor.stop(),
            resource_monitor.stop()
        ) 