"""
测试事件系统功能
"""
import asyncio
import pytest
import time
from unittest.mock import MagicMock, AsyncMock

from hive_net_py.client.core.events import (
    Event,
    ConnectionEvent,
    MessageEvent,
    StateChangeEvent,
    ErrorEvent,
    EventPriority,
    EventDispatcher,
    EventBus,
    EventSubscriber,
    event_listener,
    EventNames
)

@pytest.fixture
def dispatcher():
    """创建事件分发器实例"""
    return EventDispatcher()

@pytest.fixture
def event_bus():
    """创建事件总线实例"""
    return EventBus()

def test_event_creation():
    """测试事件创建"""
    # 基础事件
    event = Event(name="test", source="test_source", data={"key": "value"})
    assert event.name == "test"
    assert event.source == "test_source"
    assert event.data["key"] == "value"
    assert not event.propagation_stopped
    
    # 连接事件
    conn_event = ConnectionEvent(name=EventNames.CONNECT, source="client")
    assert conn_event.name == EventNames.CONNECT
    assert conn_event.source == "client"
    
    # 消息事件
    msg_event = MessageEvent(name=EventNames.MESSAGE_SENT, source="client")
    assert msg_event.name == EventNames.MESSAGE_SENT
    
    # 状态变更事件
    state_event = StateChangeEvent(
        name=EventNames.STATE_CHANGED,
        source="client",
        old_state="disconnected",
        new_state="connected"
    )
    assert state_event.old_state == "disconnected"
    assert state_event.new_state == "connected"
    
    # 错误事件
    error = ValueError("test error")
    error_event = ErrorEvent(
        name=EventNames.ERROR,
        source="client",
        error=error,
        error_type="ValueError",
        error_message="test error"
    )
    assert error_event.error == error
    assert error_event.error_type == "ValueError"
    assert error_event.error_message == "test error"

def test_event_propagation():
    """测试事件传播"""
    event = Event(name="test", source="test_source")
    assert not event.propagation_stopped
    
    event.stop_propagation()
    assert event.propagation_stopped

@pytest.mark.asyncio
async def test_event_dispatcher(dispatcher):
    """测试事件分发器"""
    # 创建监听器
    listener1 = AsyncMock()
    listener2 = MagicMock()
    
    # 添加监听器
    dispatcher.add_listener("test_event", listener1, EventPriority.HIGH)
    dispatcher.add_listener("test_event", listener2, EventPriority.NORMAL)
    
    # 验证监听器注册
    assert dispatcher.has_listeners("test_event")
    assert len(dispatcher._handlers["test_event"]) == 2
    
    # 分发事件
    event = Event(name="test_event", source="test")
    await dispatcher.dispatch(event)
    
    # 验证监听器调用
    listener1.assert_called_once_with(event)
    listener2.assert_called_once_with(event)
    
    # 移除监听器
    dispatcher.remove_listener("test_event", listener1)
    assert len(dispatcher._handlers["test_event"]) == 1

@pytest.mark.asyncio
async def test_event_priority(dispatcher):
    """测试事件优先级"""
    called_order = []
    
    async def listener_highest(event):
        called_order.append("highest")
    
    async def listener_high(event):
        called_order.append("high")
    
    async def listener_normal(event):
        called_order.append("normal")
    
    async def listener_low(event):
        called_order.append("low")
    
    # 添加不同优先级的监听器
    dispatcher.add_listener("test", listener_low, EventPriority.LOW)
    dispatcher.add_listener("test", listener_normal, EventPriority.NORMAL)
    dispatcher.add_listener("test", listener_high, EventPriority.HIGH)
    dispatcher.add_listener("test", listener_highest, EventPriority.HIGHEST)
    
    # 分发事件
    event = Event(name="test", source="test")
    await dispatcher.dispatch(event)
    
    # 验证调用顺序
    assert called_order == ["highest", "high", "normal", "low"]

@pytest.mark.asyncio
async def test_event_bus(event_bus):
    """测试事件总线"""
    # 创建分发器
    dispatcher1 = EventDispatcher()
    dispatcher2 = EventDispatcher()
    
    # 创建监听器
    listener1 = AsyncMock()
    listener2 = AsyncMock()
    
    # 添加监听器到分发器
    dispatcher1.add_listener("test", listener1)
    dispatcher2.add_listener("test", listener2)
    
    # 添加分发器到事件总线
    event_bus.attach(dispatcher1)
    event_bus.attach(dispatcher2)
    
    # 发布事件
    event = Event(name="test", source="test")
    await event_bus.publish(event)
    
    # 验证监听器调用
    listener1.assert_called_once_with(event)
    listener2.assert_called_once_with(event)
    
    # 移除分发器
    event_bus.detach(dispatcher1)
    
    # 再次发布事件
    await event_bus.publish(event)
    
    # 验证只有dispatcher2的监听器被调用
    assert listener1.call_count == 1
    assert listener2.call_count == 2

@pytest.mark.asyncio
async def test_event_subscriber(dispatcher):
    """测试事件订阅者"""
    class TestSubscriber(EventSubscriber):
        def __init__(self, dispatcher):
            self.called = []
            super().__init__(dispatcher)
        
        @event_listener("test.high", EventPriority.HIGH)
        async def on_high_priority(self, event):
            self.called.append("high")
        
        @event_listener("test.normal")
        def on_normal_priority(self, event):
            self.called.append("normal")
    
    # 创建订阅者
    subscriber = TestSubscriber(dispatcher)
    
    # 分发事件
    high_event = Event(name="test.high", source="test")
    normal_event = Event(name="test.normal", source="test")
    
    await dispatcher.dispatch(high_event)
    await dispatcher.dispatch(normal_event)
    
    # 验证处理器调用
    assert subscriber.called == ["high", "normal"]
    
    # 取消订阅
    subscriber.unsubscribe()
    
    # 清除调用记录
    subscriber.called.clear()
    
    # 再次分发事件
    await dispatcher.dispatch(high_event)
    await dispatcher.dispatch(normal_event)
    
    # 验证处理器未被调用
    assert not subscriber.called

@pytest.mark.asyncio
async def test_error_handling(dispatcher):
    """测试错误处理"""
    error_events = []
    
    async def error_listener(event):
        error_events.append(event)
    
    async def failing_listener(event):
        raise ValueError("test error")
    
    # 添加监听器
    dispatcher.add_listener("test", failing_listener)
    dispatcher.add_listener(EventNames.ERROR_HANDLER, error_listener)
    
    # 分发事件
    event = Event(name="test", source="test")
    await dispatcher.dispatch(event)
    
    # 验证错误事件
    assert len(error_events) == 1
    error_event = error_events[0]
    assert isinstance(error_event, ErrorEvent)
    assert error_event.error_type == "ValueError"
    assert error_event.error_message == "test error"

@pytest.mark.asyncio
async def test_event_propagation_control(dispatcher):
    """测试事件传播控制"""
    called = []
    
    async def listener1(event):
        called.append(1)
        event.stop_propagation()
    
    async def listener2(event):
        called.append(2)
    
    # 添加监听器
    dispatcher.add_listener("test", listener1, EventPriority.HIGH)
    dispatcher.add_listener("test", listener2, EventPriority.NORMAL)
    
    # 分发事件
    event = Event(name="test", source="test")
    await dispatcher.dispatch(event)
    
    # 验证只有高优先级监听器被调用
    assert called == [1]
    assert event.propagation_stopped 