"""
事件持久化测试
"""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from hive_net_py.client.core.events import (
    Event,
    ConnectionEvent,
    MessageEvent,
    StateChangeEvent,
    ErrorEvent
)
from hive_net_py.client.core.event_store import (
    EventStore,
    SQLiteEventStore,
    JSONEventStore,
    EventReplay
)

@pytest.fixture
def temp_db_path():
    """临时SQLite数据库路径"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)

@pytest.fixture
def temp_json_path():
    """临时JSON文件路径"""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json_path = f.name
    yield json_path
    os.unlink(json_path)

@pytest.fixture
def sqlite_store(temp_db_path):
    """SQLite事件存储"""
    return SQLiteEventStore(temp_db_path)

@pytest.fixture
def json_store(temp_json_path):
    """JSON事件存储"""
    return JSONEventStore(temp_json_path)

def create_test_events():
    """创建测试事件"""
    events = [
        ConnectionEvent(
            name="connection_established",
            source="test_client",
            timestamp=1000.0,
            connection_id="conn_1",
            status="connected",
            address="127.0.0.1:8080"
        ),
        MessageEvent(
            name="message_received",
            source="test_client",
            timestamp=1001.0,
            message_id="msg_1",
            content="test message",
            sender="server"
        ),
        StateChangeEvent(
            name="state_changed",
            source="test_client",
            timestamp=1002.0,
            old_state="INIT",
            new_state="RUNNING",
            reason="startup"
        ),
        ErrorEvent(
            name="error_occurred",
            source="test_client",
            timestamp=1003.0,
            error_code="E001",
            error_message="test error",
            stack_trace="test stack trace"
        )
    ]
    return events

@pytest.mark.asyncio
async def test_sqlite_store_basic(sqlite_store):
    """测试SQLite存储基本功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await sqlite_store.store_event(event)
    
    # 获取所有事件
    stored_events = await sqlite_store.get_events()
    assert len(stored_events) == len(events)
    
    # 验证事件内容
    for original, stored in zip(events, stored_events):
        assert stored.__class__ == original.__class__
        assert stored.name == original.name
        assert stored.source == original.source
        assert stored.timestamp == original.timestamp

@pytest.mark.asyncio
async def test_sqlite_store_filtering(sqlite_store):
    """测试SQLite存储过滤功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await sqlite_store.store_event(event)
    
    # 按时间范围过滤
    filtered_events = await sqlite_store.get_events(
        start_time=1001.0,
        end_time=1002.0
    )
    assert len(filtered_events) == 2
    
    # 按事件类型过滤
    filtered_events = await sqlite_store.get_events(
        event_types=['MessageEvent']
    )
    assert len(filtered_events) == 1
    assert isinstance(filtered_events[0], MessageEvent)
    
    # 按源过滤
    filtered_events = await sqlite_store.get_events(
        source_id='test_client'
    )
    assert len(filtered_events) == len(events)

@pytest.mark.asyncio
async def test_sqlite_store_clear(sqlite_store):
    """测试SQLite存储清除功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await sqlite_store.store_event(event)
    
    # 清除部分事件
    await sqlite_store.clear_events(before_time=1002.0)
    remaining_events = await sqlite_store.get_events()
    assert len(remaining_events) == 2
    
    # 清除所有事件
    await sqlite_store.clear_events()
    remaining_events = await sqlite_store.get_events()
    assert len(remaining_events) == 0

@pytest.mark.asyncio
async def test_json_store_basic(json_store):
    """测试JSON存储基本功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 获取所有事件
    stored_events = await json_store.get_events()
    assert len(stored_events) == len(events)
    
    # 验证事件内容
    for original, stored in zip(events, stored_events):
        assert stored.__class__ == original.__class__
        assert stored.name == original.name
        assert stored.source == original.source
        assert stored.timestamp == original.timestamp

@pytest.mark.asyncio
async def test_json_store_filtering(json_store):
    """测试JSON存储过滤功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 按时间范围过滤
    filtered_events = await json_store.get_events(
        start_time=1001.0,
        end_time=1002.0
    )
    assert len(filtered_events) == 2
    
    # 按事件类型过滤
    filtered_events = await json_store.get_events(
        event_types=['MessageEvent']
    )
    assert len(filtered_events) == 1
    assert isinstance(filtered_events[0], MessageEvent)
    
    # 按源过滤
    filtered_events = await json_store.get_events(
        source_id='test_client'
    )
    assert len(filtered_events) == len(events)

@pytest.mark.asyncio
async def test_json_store_clear(json_store):
    """测试JSON存储清除功能"""
    events = create_test_events()
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 清除部分事件
    await json_store.clear_events(before_time=1002.0)
    remaining_events = await json_store.get_events()
    assert len(remaining_events) == 2
    
    # 清除所有事件
    await json_store.clear_events()
    remaining_events = await json_store.get_events()
    assert len(remaining_events) == 0

@pytest.mark.asyncio
async def test_event_replay(json_store):
    """测试事件重放"""
    events = create_test_events()
    replay = EventReplay(json_store)
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 记录重放的事件
    replayed_events = []
    
    def event_handler(event):
        replayed_events.append(event)
    
    # 注册处理器
    for event_type in ['ConnectionEvent', 'MessageEvent', 'StateChangeEvent', 'ErrorEvent']:
        replay.register_handler(event_type, event_handler)
    
    # 重放事件
    await replay.replay_events(speed=0.1)  # 加快重放速度
    
    # 验证重放结果
    assert len(replayed_events) == len(events)
    for original, replayed in zip(events, replayed_events):
        assert replayed.__class__ == original.__class__
        assert replayed.name == original.name
        assert replayed.source == original.source
        assert replayed.timestamp == original.timestamp

@pytest.mark.asyncio
async def test_event_replay_filtering(json_store):
    """测试事件重放过滤"""
    events = create_test_events()
    replay = EventReplay(json_store)
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 记录重放的事件
    replayed_events = []
    
    def event_handler(event):
        replayed_events.append(event)
    
    # 注册处理器
    replay.register_handler('MessageEvent', event_handler)
    
    # 重放特定类型的事件
    await replay.replay_events(
        event_types=['MessageEvent'],
        speed=0.1
    )
    
    # 验证重放结果
    assert len(replayed_events) == 1
    assert isinstance(replayed_events[0], MessageEvent)

@pytest.mark.asyncio
async def test_event_replay_async_handler(json_store):
    """测试异步事件处理器"""
    events = create_test_events()
    replay = EventReplay(json_store)
    
    # 存储事件
    for event in events:
        await json_store.store_event(event)
    
    # 记录重放的事件
    replayed_events = []
    
    async def async_handler(event):
        await asyncio.sleep(0.1)  # 模拟异步操作
        replayed_events.append(event)
    
    # 注册异步处理器
    replay.register_handler('MessageEvent', async_handler)
    
    # 重放事件
    await replay.replay_events(
        event_types=['MessageEvent'],
        speed=0.1
    )
    
    # 验证重放结果
    assert len(replayed_events) == 1
    assert isinstance(replayed_events[0], MessageEvent) 