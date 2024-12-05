"""
测试消息路由系统
"""
import pytest
import time
from typing import Set

from hive_net_py.server.core.router import MessageRouter, RouteRule, create_rule
from hive_net_py.common.protocol import Message, MessageType

@pytest.fixture
def router():
    """创建路由器实例"""
    return MessageRouter()

async def handler1(message: Message):
    """测试处理器1"""
    pass

async def handler2(message: Message):
    """测试处理器2"""
    pass

@pytest.mark.asyncio
async def test_basic_routing(router):
    """测试基本路由功能"""
    # 创建规则
    rule = create_rule(
        name="test_rule",
        message_type=MessageType.DATA,
        source_pattern=r"client\d+",
        target_pattern=r"server\d*"
    )
    
    # 添加规则和处理器
    router.add_rule(rule, handler1)
    
    # 测试匹配的消息
    message = Message(
        type=MessageType.DATA,
        payload={"data": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1",
        target_id="server1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 1
    assert handler1 in handlers
    
    # 测试不匹配的消息
    message = Message(
        type=MessageType.CONNECT,
        payload={},
        sequence=2,
        timestamp=time.time(),
        source_id="client1",
        target_id="server1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 0

@pytest.mark.asyncio
async def test_payload_pattern_matching(router):
    """测试负载模式匹配"""
    # 创建带有负载模式的规则
    rule = create_rule(
        name="payload_rule",
        message_type=MessageType.DATA,
        payload_pattern={
            "action": "test",
            "value": r"\d+"
        }
    )
    
    router.add_rule(rule, handler1)
    
    # 测试匹配的消息
    message = Message(
        type=MessageType.DATA,
        payload={"action": "test", "value": "123"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 1
    assert handler1 in handlers
    
    # 测试不匹配的消息
    message = Message(
        type=MessageType.DATA,
        payload={"action": "test", "value": "abc"},
        sequence=2,
        timestamp=time.time(),
        source_id="client1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 0

@pytest.mark.asyncio
async def test_priority_routing(router):
    """测试优先级路由"""
    # 创建两个优先级不同的规则
    rule1 = create_rule(
        name="low_priority",
        message_type=MessageType.DATA,
        priority=1
    )
    
    rule2 = create_rule(
        name="high_priority",
        message_type=MessageType.DATA,
        priority=2
    )
    
    # 添加规则（故意按相反顺序添加）
    router.add_rule(rule1, handler1)
    router.add_rule(rule2, handler2)
    
    # 验证规则排序
    assert router.rules[0].priority > router.rules[1].priority
    
    # 测试消息路由
    message = Message(
        type=MessageType.DATA,
        payload={},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 2
    handlers_list = list(handlers)
    assert handler2 in handlers_list  # 高优先级处理器
    assert handler1 in handlers_list  # 低优先级处理器

@pytest.mark.asyncio
async def test_rule_removal(router):
    """测试规则移除"""
    rule = create_rule(
        name="test_rule",
        message_type=MessageType.DATA
    )
    
    router.add_rule(rule, handler1)
    assert len(router.rules) == 1
    
    router.remove_rule("test_rule")
    assert len(router.rules) == 0
    assert "test_rule" not in router.handlers
    
    # 测试移除后的消息路由
    message = Message(
        type=MessageType.DATA,
        payload={},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    
    handlers = await router.route_message(message)
    assert len(handlers) == 0 