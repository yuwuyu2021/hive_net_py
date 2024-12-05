"""
测试消息过滤器功能
"""
import pytest
import time
from typing import Set

from hive_net_py.client.core.message_filter import (
    FilterAction,
    FilterRule,
    RuleBasedFilter,
    CompositeFilter,
    create_filter_rule
)
from hive_net_py.common.protocol import Message, MessageType

@pytest.fixture
def rule_based_filter():
    """创建基于规则的过滤器实例"""
    return RuleBasedFilter()

@pytest.fixture
def composite_filter():
    """创建组合过滤器实例"""
    return CompositeFilter()

def test_filter_rule_creation():
    """测试过滤规则创建"""
    # 创建基本规则
    rule = create_filter_rule(
        name="test_rule",
        message_types={MessageType.DATA},
        source_pattern=r"client\d+",
        target_pattern=r"server\d*",
        payload_patterns={"action": "test"}
    )
    
    assert rule.name == "test_rule"
    assert MessageType.DATA in rule.message_types
    assert rule.source_pattern.pattern == r"client\d+"
    assert rule.target_pattern.pattern == r"server\d*"
    assert rule.payload_patterns["action"] == "test"
    assert rule.action == FilterAction.ACCEPT
    assert rule.priority == 0
    assert rule.modifier is None

def test_filter_rule_matching():
    """测试过滤规则匹配"""
    rule = create_filter_rule(
        name="test_rule",
        message_types={MessageType.DATA},
        source_pattern=r"client\d+",
        target_pattern=r"server\d*",
        payload_patterns={"action": "test"}
    )
    
    # 测试匹配的消息
    message = Message(
        type=MessageType.DATA,
        payload={"action": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1",
        target_id="server1"
    )
    assert rule.matches(message)
    
    # 测试不匹配的消息类型
    message = Message(
        type=MessageType.CONNECT,
        payload={"action": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1",
        target_id="server1"
    )
    assert not rule.matches(message)
    
    # 测试不匹配的源ID
    message = Message(
        type=MessageType.DATA,
        payload={"action": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="invalid",
        target_id="server1"
    )
    assert not rule.matches(message)
    
    # 测试不匹配的目标ID
    message = Message(
        type=MessageType.DATA,
        payload={"action": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1",
        target_id="invalid"
    )
    assert not rule.matches(message)
    
    # 测试不匹配的负载
    message = Message(
        type=MessageType.DATA,
        payload={"action": "invalid"},
        sequence=1,
        timestamp=time.time(),
        source_id="client1",
        target_id="server1"
    )
    assert not rule.matches(message)

@pytest.mark.asyncio
async def test_rule_based_filter(rule_based_filter):
    """测试基于规则的过滤器"""
    # 添加接受规则
    accept_rule = create_filter_rule(
        name="accept_rule",
        message_types={MessageType.DATA},
        source_pattern=r"client\d+",
        action=FilterAction.ACCEPT,
        priority=1
    )
    rule_based_filter.add_rule(accept_rule)
    
    # 添加拒绝规则
    reject_rule = create_filter_rule(
        name="reject_rule",
        message_types={MessageType.DATA},
        source_pattern=r"blocked\d+",
        action=FilterAction.REJECT,
        priority=2
    )
    rule_based_filter.add_rule(reject_rule)
    
    # 测试接受消息
    message = Message(
        type=MessageType.DATA,
        payload={},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    action, _ = await rule_based_filter.filter_message(message)
    assert action == FilterAction.ACCEPT
    
    # 测试拒绝消息
    message = Message(
        type=MessageType.DATA,
        payload={},
        sequence=1,
        timestamp=time.time(),
        source_id="blocked1"
    )
    action, _ = await rule_based_filter.filter_message(message)
    assert action == FilterAction.REJECT

@pytest.mark.asyncio
async def test_message_modification(rule_based_filter):
    """测试消息修改"""
    def modify_message(message: Message) -> Message:
        message.payload["modified"] = True
        return message
    
    # 添加修改规则
    modify_rule = create_filter_rule(
        name="modify_rule",
        message_types={MessageType.DATA},
        action=FilterAction.MODIFY,
        modifier=modify_message
    )
    rule_based_filter.add_rule(modify_rule)
    
    # 测试消息修改
    message = Message(
        type=MessageType.DATA,
        payload={"original": True},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    action, modified = await rule_based_filter.filter_message(message)
    assert action == FilterAction.MODIFY
    assert modified is not None
    assert modified.payload["modified"] is True
    assert modified.payload["original"] is True

@pytest.mark.asyncio
async def test_composite_filter(composite_filter):
    """测试组合过滤器"""
    # 创建两个规则过滤器
    filter1 = RuleBasedFilter()
    filter2 = RuleBasedFilter()
    
    # 添加规则到第一个过滤器
    modify_rule = create_filter_rule(
        name="modify_rule",
        message_types={MessageType.DATA},
        action=FilterAction.MODIFY,
        modifier=lambda m: Message(
            type=m.type,
            payload={"step1": True, **m.payload},
            sequence=m.sequence,
            timestamp=m.timestamp,
            source_id=m.source_id,
            target_id=m.target_id
        )
    )
    filter1.add_rule(modify_rule)
    
    # 添加规则到第二个过滤器
    modify_rule2 = create_filter_rule(
        name="modify_rule2",
        message_types={MessageType.DATA},
        action=FilterAction.MODIFY,
        modifier=lambda m: Message(
            type=m.type,
            payload={"step2": True, **m.payload},
            sequence=m.sequence,
            timestamp=m.timestamp,
            source_id=m.source_id,
            target_id=m.target_id
        )
    )
    filter2.add_rule(modify_rule2)
    
    # 添加过滤器到组合过滤器
    composite_filter.add_filter(filter1)
    composite_filter.add_filter(filter2)
    
    # 测试消息处理链
    message = Message(
        type=MessageType.DATA,
        payload={"original": True},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    action, modified = await composite_filter.filter_message(message)
    assert action == FilterAction.ACCEPT
    assert modified is not None
    assert modified.payload["step1"] is True
    assert modified.payload["step2"] is True
    assert modified.payload["original"] is True

@pytest.mark.asyncio
async def test_filter_priority(rule_based_filter):
    """测试过滤器优先级"""
    # 添加低优先级接受规则
    accept_rule = create_filter_rule(
        name="accept_rule",
        message_types={MessageType.DATA},
        action=FilterAction.ACCEPT,
        priority=1
    )
    rule_based_filter.add_rule(accept_rule)
    
    # 添加高优先级拒绝规则
    reject_rule = create_filter_rule(
        name="reject_rule",
        message_types={MessageType.DATA},
        action=FilterAction.REJECT,
        priority=2
    )
    rule_based_filter.add_rule(reject_rule)
    
    # 测试规则优先级
    message = Message(
        type=MessageType.DATA,
        payload={},
        sequence=1,
        timestamp=time.time(),
        source_id="client1"
    )
    action, _ = await rule_based_filter.filter_message(message)
    assert action == FilterAction.REJECT  # 高优先级规则应该先匹配 