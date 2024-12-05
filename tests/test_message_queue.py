"""
测试消息队列功能
"""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from hive_net_py.client.core.message_queue import (
    MessageQueue,
    QueueConfig,
    QueuePriority,
    QueueStats
)
from hive_net_py.common.protocol import Message, MessageType

@pytest.fixture
def queue():
    """创建测试队列实例"""
    config = QueueConfig(
        max_size=10,
        batch_size=5,
        flush_interval=0.1
    )
    return MessageQueue(config)

@pytest.mark.asyncio
async def test_queue_initialization(queue):
    """测试队列初始化"""
    assert queue.config.max_size == 10
    assert queue.config.batch_size == 5
    assert queue.config.flush_interval == 0.1
    assert not queue._running
    assert queue._flush_task is None
    
    # 验证统计信息初始化
    assert queue.stats.total_enqueued == 0
    assert queue.stats.total_dequeued == 0
    assert queue.stats.total_dropped == 0
    assert queue.stats.queue_size == 0
    
    # 验证优先级队列初始化
    for priority in QueuePriority:
        assert priority in queue._queues
        assert queue._queues[priority].maxsize == queue.config.max_size

@pytest.mark.asyncio
async def test_queue_start_stop(queue):
    """测试队列启动和停止"""
    # 测试启动
    await queue.start()
    assert queue._running
    assert queue._flush_task is not None
    
    # 测试重复启动
    await queue.start()
    assert queue._running
    
    # 测试停止
    await queue.stop()
    assert not queue._running
    assert queue._flush_task is None
    
    # 测试重复停止
    await queue.stop()
    assert not queue._running

@pytest.mark.asyncio
async def test_message_enqueue(queue):
    """测试消息入队"""
    await queue.start()
    
    try:
        # 创建测试消息
        message = Message(
            type=MessageType.DATA,
            payload={"test": "data"},
            sequence=1,
            timestamp=time.time(),
            source_id="test_client"
        )
        
        # 测试正常入队
        success = await queue.enqueue(message)
        assert success
        assert queue.stats.total_enqueued == 1
        assert queue.stats.queue_size == 1
        
        # 测试队列满时的情况
        for _ in range(queue.config.max_size):
            await queue.enqueue(message)
        
        # 下一个消息应该被丢弃
        success = await queue.enqueue(message)
        assert not success
        assert queue.stats.total_dropped == 1
    finally:
        await queue.stop()

@pytest.mark.asyncio
async def test_message_handler_registration(queue):
    """测试消息处理器注册"""
    # 创建测试处理器
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    
    # 注册处理器
    await queue.register_handler(MessageType.DATA, handler1)
    await queue.register_handler(MessageType.DATA, handler2)
    assert len(queue._handlers[MessageType.DATA]) == 2
    
    # 注销处理器
    await queue.unregister_handler(MessageType.DATA, handler1)
    assert len(queue._handlers[MessageType.DATA]) == 1
    
    # 注销最后一个处理器
    await queue.unregister_handler(MessageType.DATA, handler2)
    assert MessageType.DATA not in queue._handlers

@pytest.mark.asyncio
async def test_message_processing(queue):
    """测试消息处理"""
    await queue.start()
    
    try:
        # 创建测试处理器
        handler = AsyncMock()
        await queue.register_handler(MessageType.DATA, handler)
        
        # 创建测试消息
        message = Message(
            type=MessageType.DATA,
            payload={"test": "data"},
            sequence=1,
            timestamp=time.time(),
            source_id="test_client"
        )
        
        # 入队消息
        await queue.enqueue(message)
        
        # 等待消息处理
        await asyncio.sleep(queue.config.flush_interval * 2)
        
        # 验证处理器被调用
        handler.assert_called_once()
        assert queue.stats.total_dequeued == 1
    finally:
        await queue.stop()

@pytest.mark.asyncio
async def test_priority_handling(queue):
    """测试优先级处理"""
    await queue.start()
    
    try:
        # 创建测试处理器
        handler = AsyncMock()
        processed_messages = []
        
        async def test_handler(message):
            processed_messages.append(message)
            await asyncio.sleep(0.01)  # 模拟处理时间
        
        handler.side_effect = test_handler
        await queue.register_handler(MessageType.DATA, handler)
        
        # 创建不同优先级的消息
        messages = []
        for i, priority in enumerate(QueuePriority):
            message = Message(
                type=MessageType.DATA,
                payload={"priority": priority.name},
                sequence=i,
                timestamp=time.time(),
                source_id="test_client"
            )
            messages.append((message, priority))
        
        # 按相反顺序入队消息
        for message, priority in reversed(messages):
            await queue.enqueue(message, priority)
        
        # 等待消息处理
        await asyncio.sleep(queue.config.flush_interval * 3)
        
        # 验证处理顺序（高优先级应该先处理）
        assert len(processed_messages) == 3
        assert processed_messages[0].payload["priority"] == QueuePriority.HIGH.name
        assert processed_messages[1].payload["priority"] == QueuePriority.NORMAL.name
        assert processed_messages[2].payload["priority"] == QueuePriority.LOW.name
    finally:
        await queue.stop()

@pytest.mark.asyncio
async def test_batch_processing(queue):
    """测试批量处理"""
    await queue.start()
    
    try:
        # 创建测试处理器
        handler = AsyncMock()
        batch_sizes = []
        
        async def test_handler(message):
            # 记录每次处理的批次大小
            if not batch_sizes or batch_sizes[-1] >= queue.config.batch_size:
                batch_sizes.append(1)
            else:
                batch_sizes[-1] += 1
            await asyncio.sleep(0.01)  # 模拟处理时间
        
        handler.side_effect = test_handler
        await queue.register_handler(MessageType.DATA, handler)
        
        # 入队多个消息
        message = Message(
            type=MessageType.DATA,
            payload={"test": "data"},
            sequence=1,
            timestamp=time.time(),
            source_id="test_client"
        )
        
        for _ in range(queue.config.batch_size * 2):
            await queue.enqueue(message)
        
        # 等待消息处理
        await asyncio.sleep(queue.config.flush_interval * 3)
        
        # 验证批量处理
        assert len(batch_sizes) >= 2  # 至少有两个批次
        assert all(size <= queue.config.batch_size for size in batch_sizes)
        assert sum(batch_sizes) == queue.config.batch_size * 2
    finally:
        await queue.stop() 