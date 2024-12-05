"""
测试客户端核心功能
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

from hive_net_py.client.core.client import (
    HiveClient,
    ClientState,
    ConnectionConfig
)
from hive_net_py.client.core.message_queue import (
    QueueConfig,
    QueuePriority,
    MessageQueue
)
from hive_net_py.client.core.message_filter import MessageFilter, FilterAction
from hive_net_py.client.core.events import (
    Event, ConnectionEvent, MessageEvent, StateChangeEvent, 
    ErrorEvent, EventBus, EventPriority
)

@pytest.fixture
def connection_config():
    """创建连接配置"""
    return ConnectionConfig(
        host="localhost",
        port=8080,
        timeout=5.0,
        retry_interval=1.0,
        max_retries=2
    )

@pytest.fixture
def queue_config():
    """创建队列配置"""
    return QueueConfig(
        max_size=100,
        batch_size=10,
        flush_interval=0.1
    )

@pytest.fixture
def message_filter():
    """创建消息过滤器"""
    filter_mock = AsyncMock(spec=MessageFilter)
    # 设置filter_message的返值为(FilterAction.ACCEPT, None)
    filter_mock.filter_message.return_value = (FilterAction.ACCEPT, None)
    return filter_mock

@pytest.fixture
def event_store():
    """创建事件存储器"""
    store_mock = AsyncMock()
    events = []
    
    async def store_event(event):
        events.append(event)
    
    async def get_events(start_time=None, end_time=None, event_types=None):
        return events
    
    async def clear_events(before_time=None):
        events.clear()
    
    store_mock.store_event = store_event
    store_mock.get_events = get_events
    store_mock.clear_events = clear_events
    return store_mock

@pytest.fixture
async def client(connection_config, queue_config, message_filter, event_store):
    """创建客户端实例"""
    client = HiveClient(
        connection_config=connection_config,
        queue_config=queue_config,
        message_filter=message_filter,
        event_store=event_store
    )
    try:
        yield client
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_client_initialization(client, connection_config):
    """测试客户端初始化"""
    client = await client.__anext__()
    assert client.config == connection_config
    assert client.state == ClientState.INIT
    assert client.message_queue is not None
    assert client.message_filter is not None
    assert client.performance_monitor is not None
    assert client.event_bus is not None
    assert client.event_store is not None

@pytest.mark.asyncio
async def test_client_connect(client):
    """测试客户端连接"""
    client = await client.__anext__()
    await client.connect()
    assert client.state == ClientState.CONNECTED

    # 验证事件发布
    events = await client.get_events()
    event_names = [e.name for e in events]
    assert "client_connecting" in event_names
    assert "connection_established" in event_names
    assert "client_connected" in event_names

@pytest.mark.asyncio
async def test_client_disconnect(client):
    """试客户端断开连接"""
    client = await client.__anext__()
    await client.connect()
    await client.disconnect()
    assert client.state == ClientState.DISCONNECTED

    # 验证事件发布
    events = await client.get_events()
    event_names = [e.name for e in events]
    assert "client_disconnecting" in event_names
    assert "connection_closed" in event_names
    assert "client_disconnected" in event_names

@pytest.mark.asyncio
async def test_client_send_message(client):
    """测试发送消息"""
    client = await client.__anext__()
    test_message = {"type": "test", "content": "Hello"}
    await client.connect()
    await client.send_message(test_message)

    # 验证消息过滤器调用
    client.message_filter.filter_message.assert_called_once()

    # 验证事件发布
    events = await client.get_events()
    message_events = [e for e in events if isinstance(e, MessageEvent)]
    assert len(message_events) > 0
    assert message_events[-1].name == "message_sent"

@pytest.mark.asyncio
async def test_client_receive_message(client):
    """测试接收消息"""
    client = await client.__anext__()
    test_message = {"type": "test", "content": "Hello"}
    await client.connect()
    
    # 放入测试消息
    await client.message_queue.put(test_message)
    
    # 接收消息
    received_message = await client.receive_message()
    assert received_message == test_message

    # 验证消息过滤器调用
    client.message_filter.filter_message.assert_called()

    # 验证事件发布
    events = await client.get_events()
    message_events = [e for e in events if isinstance(e, MessageEvent)]
    assert len(message_events) > 0
    assert message_events[-1].name == "message_received"

@pytest.mark.asyncio
async def test_client_filtered_message(client):
    """测试消息过滤"""
    client = await client.__anext__()
    test_message = {"type": "filtered", "content": "Should be filtered"}
    client.message_filter.filter_message.return_value = (FilterAction.REJECT, None)
    
    await client.connect()
    await client.send_message(test_message)
    
    # 验证消息被过滤
    received_message = await client.receive_message()
    assert received_message is None

@pytest.mark.asyncio
async def test_client_connection_error(client):
    """测试连接错误处理"""
    client = await client.__anext__()
    # 模拟连接错误
    with patch.object(client, '_setup_event_handlers', side_effect=Exception("Connection failed")):
        with pytest.raises(Exception):
            await client.connect()
        
        assert client.state == ClientState.ERROR
        
        # 验证错误事件
        events = await client.get_events()
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) > 0
        assert error_events[-1].name == "connection_error"

@pytest.mark.asyncio
async def test_client_event_management(client):
    """测试事件管理"""
    client = await client.__anext__()
    # 生成一些测试事件
    await client.connect()
    await client.send_message({"type": "test"})
    await client.disconnect()
    
    # 获取所有事
    all_events = await client.get_events()
    assert len(all_events) > 0
    
    # 获取特定时间范围的事件
    current_time = time.time()
    events = await client.get_events(
        start_time=current_time - 3600,
        end_time=current_time
    )
    assert len(events) > 0
    
    # 清除事件
    await client.clear_events()
    events = await client.get_events()
    assert len(events) == 0

@pytest.mark.asyncio
async def test_client_close(client):
    """测试客户端关闭"""
    client = await client.__anext__()
    await client.connect()
    await client.close()
    
    assert client.state == ClientState.DISCONNECTED
    assert client.message_queue.is_closed()
    
@pytest.mark.asyncio
async def test_message_queue_priority(client):
    """测试消息队列优先级"""
    client = await client.__anext__()
    await client.connect()
    
    # 发送不同优先级的消息
    high_priority = {"type": "high", "content": "High priority"}
    normal_priority = {"type": "normal", "content": "Normal priority"}
    low_priority = {"type": "low", "content": "Low priority"}
    
    await client.message_queue.put(low_priority, QueuePriority.LOW)
    await client.message_queue.put(normal_priority, QueuePriority.NORMAL)
    await client.message_queue.put(high_priority, QueuePriority.HIGH)
    
    # 验证消息按优先级顺序接收
    received_high = await client.receive_message()
    received_normal = await client.receive_message()
    received_low = await client.receive_message()
    
    assert received_high == high_priority
    assert received_normal == normal_priority
    assert received_low == low_priority

@pytest.mark.asyncio
async def test_event_propagation(client):
    """测试事件传播"""
    client = await client.__anext__()
    events_received = []
    
    # 注册事件处理器
    async def event_handler(event: Event):
        events_received.append(event)
        if event.name == "test.stop":
            event.stop_propagation()
    
    # 注册两个事件处理器
    client.event_bus.subscribe("test.*", event_handler, EventPriority.HIGH)
    client.event_bus.subscribe("test.*", event_handler, EventPriority.LOW)
    
    # 发布测试事件
    test_event1 = Event(name="test.continue", source="test")
    test_event2 = Event(name="test.stop", source="test")
    test_event3 = Event(name="test.after", source="test")
    
    await client.event_bus.publish(test_event1)  # 应该被两个处理器接收
    await client.event_bus.publish(test_event2)  # 应该只被第一个处理器接收，因为它会停止传播
    await client.event_bus.publish(test_event3)  # 应该被两个处理器接收
    
    # 验证事件传播
    assert len(events_received) == 5  # continue(2) + stop(1) + after(2)
    
    # 验证事件顺序
    assert events_received[0].name == "test.continue"  # HIGH priority
    assert events_received[1].name == "test.continue"  # LOW priority
    assert events_received[2].name == "test.stop"      # HIGH priority only
    assert events_received[3].name == "test.after"     # HIGH priority
    assert events_received[4].name == "test.after"     # LOW priority

@pytest.mark.asyncio
async def test_concurrent_message_handling(client):
    """测试并发消息处理"""
    client = await client.__anext__()
    await client.connect()
    
    # 创建多个并发任务发送消息
    message_count = 100
    send_tasks = []
    for i in range(message_count):
        message = {"type": "test", "id": i}
        task = asyncio.create_task(client.send_message(message))
        send_tasks.append(task)
    
    # 等待所有发送任务完成
    await asyncio.gather(*send_tasks)
    
    # 验证所有消息都被正确处理
    received_messages = []
    for _ in range(message_count):
        message = await client.receive_message()
        if message:
            received_messages.append(message)
    
    assert len(received_messages) == message_count
    received_ids = {msg["id"] for msg in received_messages}
    assert len(received_ids) == message_count

@pytest.mark.asyncio
async def test_edge_cases(client):
    """测试边界条件"""
    client = await client.__anext__()
    await client.connect()
    
    # 测试空消息
    await client.send_message({})
    received = await client.receive_message()
    assert received == {}
    
    # 测试大消息
    large_content = "x" * 1024 * 1024  # 1MB
    large_message = {"type": "large", "content": large_content}
    await client.send_message(large_message)
    received = await client.receive_message()
    assert received == large_message
    
    # 测试特殊字符
    special_message = {
        "type": "special",
        "content": "!@#$%^&*()_+-=[]{}|;:'\",.<>?/~`"
    }
    await client.send_message(special_message)
    received = await client.receive_message()
    assert received == special_message
    
    # 测试Unicode字符
    unicode_message = {
        "type": "unicode",
        "content": "你好世界🌍"
    }
    await client.send_message(unicode_message)
    received = await client.receive_message()
    assert received == unicode_message

@pytest.mark.asyncio
async def test_error_recovery(client):
    """测试错误恢复"""
    client = await client.__anext__()
    
    # 模拟连接错误和恢复
    with patch.object(client, '_setup_event_handlers', side_effect=Exception("Connection failed")):
        with pytest.raises(Exception):
            await client.connect()
        assert client.state == ClientState.ERROR
    
    # 尝试恢复
    await client.connect()
    assert client.state == ClientState.CONNECTED
    
    # 验证可以正常发送和接收消息
    test_message = {"type": "test", "content": "Recovery test"}
    await client.send_message(test_message)
    received = await client.receive_message()
    assert received == test_message

@pytest.mark.asyncio
async def test_message_filter_chain(client):
    """测试消息过滤器链"""
    client = await client.__anext__()
    await client.connect()
    
    # 创建多个过滤器
    filter_results = []
    
    class TestFilter(MessageFilter):
        def __init__(self, name, action):
            self.name = name
            self.action = action
            
        async def filter_message(self, message):
            filter_results.append(self.name)
            return self.action, message
    
    # 设置过滤器链
    client.message_filter = TestFilter("filter1", FilterAction.ACCEPT)
    
    # 测试消息过滤
    test_message = {"type": "test", "content": "Filter chain test"}
    await client.send_message(test_message)
    
    # 验证过滤器被正确调用
    assert len(filter_results) == 1
    assert filter_results[0] == "filter1"

@pytest.mark.asyncio
async def test_queue_overflow(client):
    """测试队列溢出处理"""
    client = await client.__anext__()
    await client.connect()
    
    # 创建一个小容量的队列配置
    small_queue_config = QueueConfig(max_size=5, batch_size=2, flush_interval=0.1)
    client.message_queue = MessageQueue(small_queue_config)
    await client.message_queue.start()
    
    # 尝试发送超过队列容量的消息
    messages_sent = 0
    for i in range(10):
        success = await client.message_queue.put(
            {"type": "test", "id": i},
            QueuePriority.NORMAL
        )
        if success:
            messages_sent += 1
    
    # 验证部分消息被丢弃
    assert messages_sent <= small_queue_config.max_size
    
    # 验证队列统计信息
    assert client.message_queue.stats.total_dropped > 0
    