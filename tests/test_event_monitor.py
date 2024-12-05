"""
事件监控测试
"""
import asyncio
import time
from typing import List
import pytest

from hive_net_py.client.core.events import (
    Event,
    ErrorEvent,
    EventBus
)
from hive_net_py.client.core.event_store import (
    EventStore,
    JSONEventStore
)
from hive_net_py.client.core.event_monitor import (
    AlertLevel,
    AlertRule,
    Alert,
    AlertHandler,
    LogAlertHandler,
    EventMonitor,
    create_error_rate_rule,
    create_connection_failure_rule,
    create_performance_rule
)

class TestAlertHandler(AlertHandler):
    """测试用告警处理器"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
    
    async def handle_alert(self, alert: Alert):
        """记录告警"""
        self.alerts.append(alert)

@pytest.fixture
def event_bus():
    """创建事件总线"""
    return EventBus()

@pytest.fixture
def event_store(tmp_path):
    """创建事件存储"""
    return JSONEventStore(tmp_path / "events.json")

@pytest.fixture
def alert_handler():
    """创建告警处理器"""
    return TestAlertHandler()

@pytest.fixture
def event_monitor(event_bus, event_store, alert_handler):
    """创建事件监控器"""
    monitor = EventMonitor(event_bus, event_store)
    monitor.add_handler(alert_handler)
    return monitor

@pytest.mark.asyncio
async def test_error_rate_rule(event_monitor, event_bus, alert_handler):
    """测试错误率告警规则"""
    # 创建规则
    rule = create_error_rate_rule(
        name="test_error_rate",
        window=5.0,     # 5秒窗口
        threshold=3,    # 3个错误
        level=AlertLevel.ERROR
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送错误事件
        for i in range(4):  # 超过阈值
            await event_bus.publish(ErrorEvent(
                name="test_error",
                source="test_source",
                timestamp=time.time(),
                error_code="E001",
                error_message=f"Test error {i}",
                stack_trace=""
            ))
            await asyncio.sleep(0.1)
        
        # 等待处理
        await asyncio.sleep(1)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        alert = alert_handler.alerts[0]
        assert alert.rule_name == "test_error_rate"
        assert alert.level == AlertLevel.ERROR
        assert len(alert.events) == 1  # 单个事件触发
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_connection_failure_rule(event_monitor, event_bus, alert_handler):
    """测试连接失败告警规则"""
    # 创建规则
    rule = create_connection_failure_rule(
        name="test_connection_failure",
        pattern=r"test_.*",
        window=5.0,     # 5秒窗口
        threshold=2,    # 2次失败
        level=AlertLevel.WARNING
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送连接错误事件
        for i in range(3):  # 超过阈值
            await event_bus.publish(ErrorEvent(
                name="connection_error",
                source="test_client",
                timestamp=time.time(),
                error_code="CONNECTION_FAILED",
                error_message=f"Connection failed {i}",
                stack_trace=""
            ))
            await asyncio.sleep(0.1)
        
        # 等待处理
        await asyncio.sleep(1)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        alert = alert_handler.alerts[0]
        assert alert.rule_name == "test_connection_failure"
        assert alert.level == AlertLevel.WARNING
        assert len(alert.events) == 1
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_performance_rule(event_monitor, event_bus, alert_handler):
    """测试性能指标告警规则"""
    # 创建规则
    rule = create_performance_rule(
        name="test_performance",
        metric_name="cpu_usage",
        threshold=80.0,  # CPU使用率阈值
        window=5.0,      # 5秒窗口
        level=AlertLevel.WARNING
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送性能事件
        await event_bus.publish(Event(
            name="cpu_usage",
            source="test_system",
            timestamp=time.time(),
            value="85.0"
        ))
        
        # 等待处理
        await asyncio.sleep(1)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        alert = alert_handler.alerts[0]
        assert alert.rule_name == "test_performance"
        assert alert.level == AlertLevel.WARNING
        assert len(alert.events) == 1
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_alert_cooldown(event_monitor, event_bus, alert_handler):
    """测试告警冷���"""
    # 创建规则
    rule = create_error_rate_rule(
        name="test_cooldown",
        window=5.0,      # 5秒窗口
        threshold=1,     # 1个错误就告警
        level=AlertLevel.ERROR
    )
    rule.cooldown = 2.0  # 设置2秒冷却时间
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送第一个错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 1",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证第一次告警
        assert len(alert_handler.alerts) == 1
        
        # 立即发送第二个错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 2",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证没有新告警（冷却中）
        assert len(alert_handler.alerts) == 1
        
        # 等待冷却时间过去
        await asyncio.sleep(2)
        
        # 发送第三个错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 3",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证新告警
        assert len(alert_handler.alerts) == 2
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_event_aggregation(event_monitor, event_bus, alert_handler):
    """测试事件聚合"""
    # 创建规则
    rule = create_error_rate_rule(
        name="test_aggregation",
        window=5.0,      # 5秒窗口
        threshold=3,     # 3个错误才告警
        level=AlertLevel.ERROR
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送两个错误事件（不足以触发告警）
        for i in range(2):
            await event_bus.publish(ErrorEvent(
                name="test_error",
                source="test_source",
                timestamp=time.time(),
                error_code="E001",
                error_message=f"Test error {i}",
                stack_trace=""
            ))
            await asyncio.sleep(0.1)
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证没有告警
        assert len(alert_handler.alerts) == 0
        
        # 发送第三个错误事件（达到阈值）
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 3",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        alert = alert_handler.alerts[0]
        assert alert.rule_name == "test_aggregation"
        assert len(alert.events) == 1
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_multiple_handlers(event_monitor, event_bus):
    """测试多个告警处理器"""
    # 创建多个处理器
    handler1 = TestAlertHandler()
    handler2 = TestAlertHandler()
    handler3 = LogAlertHandler()
    
    event_monitor.add_handler(handler1)
    event_monitor.add_handler(handler2)
    event_monitor.add_handler(handler3)
    
    # 创建规则
    rule = create_error_rate_rule(
        name="test_handlers",
        window=5.0,
        threshold=1,
        level=AlertLevel.ERROR
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证所有处理器都收到告警
        assert len(handler1.alerts) == 1
        assert len(handler2.alerts) == 1
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_rule_removal(event_monitor, event_bus, alert_handler):
    """测试规则移除"""
    # 创建规则
    rule = create_error_rate_rule(
        name="test_removal",
        window=5.0,
        threshold=1,
        level=AlertLevel.ERROR
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送第一个错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 1",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        
        # 移除规则
        event_monitor.remove_rule("test_removal")
        
        # 发送第二个错误事件
        await event_bus.publish(ErrorEvent(
            name="test_error",
            source="test_source",
            timestamp=time.time(),
            error_code="E001",
            error_message="Test error 2",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证没有新告警
        assert len(alert_handler.alerts) == 1
        
    finally:
        await event_monitor.stop()

@pytest.mark.asyncio
async def test_source_pattern_matching(event_monitor, event_bus, alert_handler):
    """测试事件源匹配"""
    # 创建规则
    rule = create_connection_failure_rule(
        name="test_source_pattern",
        pattern=r"client_\d+",  # 只匹配 client_数字 格式
        window=5.0,
        threshold=1,
        level=AlertLevel.WARNING
    )
    event_monitor.add_rule(rule)
    
    # 启动监控器
    await event_monitor.start()
    
    try:
        # 发送匹配的错误事件
        await event_bus.publish(ErrorEvent(
            name="connection_error",
            source="client_123",
            timestamp=time.time(),
            error_code="CONNECTION_FAILED",
            error_message="Test error 1",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证告警
        assert len(alert_handler.alerts) == 1
        
        # 发送不匹配的错误事件
        await event_bus.publish(ErrorEvent(
            name="connection_error",
            source="server_1",
            timestamp=time.time(),
            error_code="CONNECTION_FAILED",
            error_message="Test error 2",
            stack_trace=""
        ))
        
        # 等待处理
        await asyncio.sleep(0.5)
        
        # 验证没有新告警
        assert len(alert_handler.alerts) == 1
        
    finally:
        await event_monitor.stop() 