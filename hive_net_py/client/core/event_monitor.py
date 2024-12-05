"""
HiveNet 事件监控模块
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union
import re

from .events import Event, ErrorEvent, EventBus
from .event_store import EventStore

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = auto()      # 信息
    WARNING = auto()   # 警告
    ERROR = auto()     # 错误
    CRITICAL = auto()  # 严重
    
    def get_color(self) -> str:
        """获取告警级别对应的颜色"""
        return {
            AlertLevel.INFO: "#1E88E5",     # 蓝色
            AlertLevel.WARNING: "#FFC107",   # 黄色
            AlertLevel.ERROR: "#E53935",     # 红色
            AlertLevel.CRITICAL: "#B71C1C"   # 深红色
        }[self]

@dataclass
class AlertRule:
    """告警规则"""
    name: str                                     # 规则名称
    event_types: Set[str]                        # 监控的事件类型
    condition: Callable[[Event], bool]           # 告警条件
    level: AlertLevel                            # 告警级别
    description: str                             # 规则描述
    cooldown: float = 60.0                       # 告警冷却时间(秒)
    source_pattern: Optional[Pattern] = None     # 事件源匹配模式
    aggregation_window: float = 60.0            # 聚合窗口时间(秒)
    aggregation_threshold: int = 1              # 聚合阈值
    last_alert_time: float = field(default=0.0)  # 上次告警时间
    alert_count: int = field(default=0)          # 当前窗口告警次数

@dataclass
class Alert:
    """告警信息"""
    rule_name: str           # 触发的规则名称
    level: AlertLevel        # 告警级别
    message: str            # 告警消息
    source: str            # 告警源
    timestamp: float       # 告警时间
    events: List[Event]    # 相关事件列表
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    
    def get_truncated_message(self, max_length: int) -> str:
        """获取截断后的消息"""
        if len(self.message) <= max_length:
            return self.message
        return self.message[:max_length-3] + "..."

class AlertHandler:
    """告警处理器基类"""
    
    async def handle_alert(self, alert: Alert):
        """处理告警"""
        pass

class LogAlertHandler(AlertHandler):
    """日志告警处理器"""
    
    async def handle_alert(self, alert: Alert):
        """将告警写入日志"""
        level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }
        logger.log(
            level_map[alert.level],
            f"[{alert.rule_name}] {alert.message} "
            f"(source: {alert.source}, events: {len(alert.events)})"
        )

class EmailAlertHandler(AlertHandler):
    """邮件告警处理器"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_config = smtp_config
    
    async def handle_alert(self, alert: Alert):
        """发送告警邮件"""
        # TODO: 实现邮件发送逻辑
        logger.info(f"发送告警邮件: {alert.message}")

class WebhookAlertHandler(AlertHandler):
    """Webhook告警处理器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def handle_alert(self, alert: Alert):
        """发送告警到Webhook"""
        # TODO: 实现Webhook调用逻辑
        logger.info(f"发送告警到Webhook: {alert.message}")

class EventMonitor:
    """事件监控器"""
    
    def __init__(self, event_bus: EventBus,
                 event_store: Optional[EventStore] = None):
        """
        初始化事件监控器
        
        Args:
            event_bus: 事件总线
            event_store: 事件存储器
        """
        self.event_bus = event_bus
        self.event_store = event_store
        self.rules: List[AlertRule] = []
        self.handlers: List[AlertHandler] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
    
    def remove_rule(self, rule: AlertRule):
        """移除告警规则"""
        if rule in self.rules:
            self.rules.remove(rule)
    
    def add_handler(self, handler: AlertHandler):
        """添加告警处理器"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: AlertHandler):
        """移除告警处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    async def start(self):
        """启动监控器"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("事件监控器已启动")
    
    async def stop(self):
        """停止监控器"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("事件监控器已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self._running:
                try:
                    # 获取事件
                    event = await self.event_bus.get()
                    
                    # 存储事件
                    if self.event_store:
                        await self.event_store.store_event(event)
                    
                    # 检查规则
                    await self._check_rules(event)
                    
                except Exception as e:
                    logger.error(f"处理事件时出错: {e}")
        except asyncio.CancelledError:
            pass
    
    async def _check_rules(self, event: Event):
        """检查告警规则"""
        current_time = time.time()
        
        for rule in self.rules:
            try:
                # 检查事件类型
                if event.__class__.__name__ not in rule.event_types:
                    continue
                
                # 检查事件源
                if rule.source_pattern and not rule.source_pattern.match(event.source):
                    continue
                
                # 检查冷却时间
                if current_time - rule.last_alert_time < rule.cooldown:
                    continue
                
                # 检查告警条件
                if not rule.condition(event):
                    continue
                
                # 增加计数
                rule.alert_count += 1
                
                # 检查是否达到聚合阈值
                if rule.alert_count >= rule.aggregation_threshold:
                    # 创建告警
                    alert = Alert(
                        rule_name=rule.name,
                        level=rule.level,
                        message=rule.description,
                        source=event.source,
                        timestamp=current_time,
                        events=[event],
                        context={}
                    )
                    
                    # 处理告警
                    await self._handle_alert(alert)
                    
                    # 更新规则状态
                    rule.last_alert_time = current_time
                    rule.alert_count = 0
                
            except Exception as e:
                logger.error(f"检查规则 {rule.name} 时出错: {e}")
    
    async def _handle_alert(self, alert: Alert):
        """处理告警"""
        for handler in self.handlers:
            try:
                await handler.handle_alert(alert)
            except Exception as e:
                logger.error(f"处理告警时出错: {e}")

def create_error_rate_rule(
    name: str,
    window: float = 300.0,  # 5分钟窗口
    threshold: int = 10,    # 10个错误
    level: AlertLevel = AlertLevel.ERROR
) -> AlertRule:
    """
    创建错误率告警规则
    
    Args:
        name: 规则名称
        window: 聚合窗口时间(秒)
        threshold: 错误数阈值
        level: 告警级别
    """
    return AlertRule(
        name=name,
        event_types={"ErrorEvent"},
        condition=lambda event: isinstance(event, ErrorEvent),
        level=level,
        description="检测到高错误率: {count}个错误在{window}秒内",
        aggregation_window=window,
        aggregation_threshold=threshold
    )

def create_connection_failure_rule(
    name: str,
    pattern: str = r".*",
    window: float = 300.0,  # 5分钟窗口
    threshold: int = 5,     # 5次失败
    level: AlertLevel = AlertLevel.WARNING
) -> AlertRule:
    """
    创建连接失败告警规则
    
    Args:
        name: 规则名称
        pattern: 事件源匹配模式
        window: 聚合窗口时间(秒)
        threshold: 失败次数阈值
        level: 告警级别
    """
    return AlertRule(
        name=name,
        event_types={"ErrorEvent"},
        condition=lambda event: (
            isinstance(event, ErrorEvent) and 
            "connection" in event.error_code.lower()
        ),
        level=level,
        description="检测到连接异常: {count}次失败在{window}秒内",
        source_pattern=re.compile(pattern),
        aggregation_window=window,
        aggregation_threshold=threshold
    )

def create_performance_rule(
    name: str,
    metric_name: str,
    threshold: float,
    window: float = 300.0,  # 5分钟窗口
    level: AlertLevel = AlertLevel.WARNING
) -> AlertRule:
    """
    创建性能指标告警规则
    
    Args:
        name: 规则名称
        metric_name: 指标名称
        threshold: 指标阈值
        window: 聚合窗口时间(秒)
        level: 告警级别
    """
    return AlertRule(
        name=name,
        event_types={"PerformanceEvent"},
        condition=lambda event: (
            event.name == metric_name and
            float(event.value) > threshold
        ),
        level=level,
        description=f"{metric_name}超过阈值{threshold}: 当前值{{event.value}}",
        aggregation_window=window,
        aggregation_threshold=1
    ) 