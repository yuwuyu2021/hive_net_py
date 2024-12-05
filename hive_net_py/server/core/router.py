"""
HiveNet 消息路由系统
"""
import logging
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union
import re
from dataclasses import dataclass, field

from ...common.protocol import Message, MessageType

logger = logging.getLogger(__name__)

@dataclass
class RouteRule:
    """路由规则"""
    name: str
    message_type: Optional[MessageType] = None  # 消息类型匹配
    source_pattern: Optional[Pattern] = None    # 源ID匹配模式
    target_pattern: Optional[Pattern] = None    # 目标ID匹配模式
    payload_pattern: Dict[str, Union[str, Pattern, Any]] = field(default_factory=dict)  # 负载匹配模式
    priority: int = 0  # 优先级，数字越大优先级越高

    def matches(self, message: Message) -> bool:
        """检查消息是否匹配规则"""
        # 检查消息类型
        if self.message_type and message.type != self.message_type:
            return False
        
        # 检查源ID
        if self.source_pattern and not self.source_pattern.match(message.source_id):
            return False
        
        # 检查目标ID
        if self.target_pattern and (
            not message.target_id or 
            not self.target_pattern.match(message.target_id)
        ):
            return False
        
        # 检查负载
        for key, pattern in self.payload_pattern.items():
            if key not in message.payload:
                return False
            
            value = message.payload[key]
            if isinstance(pattern, Pattern):
                if not pattern.match(str(value)):
                    return False
            elif isinstance(pattern, str) and isinstance(value, str):
                if not re.match(pattern, value):
                    return False
            elif pattern != value:
                return False
        
        return True

class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self.rules: List[RouteRule] = []
        self.handlers: Dict[str, List[Callable]] = {}
    
    def add_rule(self, rule: RouteRule, handler: Callable):
        """添加路由规则和处理器"""
        self.rules.append(rule)
        if rule.name not in self.handlers:
            self.handlers[rule.name] = []
        self.handlers[rule.name].append(handler)
        
        # 按优先级排序规则
        self.rules.sort(key=lambda x: x.priority, reverse=True)
        logger.info(f"添加路由规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除路由规则"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        self.handlers.pop(rule_name, None)
        logger.info(f"移除路由规则: {rule_name}")
    
    async def route_message(self, message: Message) -> Set[Callable]:
        """路由消息到匹配的处理器"""
        matched_handlers = set()
        
        for rule in self.rules:
            if rule.matches(message):
                handlers = self.handlers.get(rule.name, [])
                matched_handlers.update(handlers)
                logger.debug(f"消息匹配规则 {rule.name}")
        
        if not matched_handlers:
            logger.warning(f"消息没有匹配的处理器: {message.type}")
        
        return matched_handlers

def create_rule(
    name: str,
    message_type: Optional[MessageType] = None,
    source_pattern: Optional[str] = None,
    target_pattern: Optional[str] = None,
    payload_pattern: Optional[Dict[str, Any]] = None,
    priority: int = 0
) -> RouteRule:
    """创建路由规则的辅助函数"""
    # 处理负载模式
    processed_payload_pattern = {}
    if payload_pattern:
        for key, pattern in payload_pattern.items():
            if isinstance(pattern, str) and any(c in pattern for c in r'.^$*+?{}[]|\()'):
                processed_payload_pattern[key] = re.compile(pattern)
            else:
                processed_payload_pattern[key] = pattern
    
    return RouteRule(
        name=name,
        message_type=message_type,
        source_pattern=re.compile(source_pattern) if source_pattern else None,
        target_pattern=re.compile(target_pattern) if target_pattern else None,
        payload_pattern=processed_payload_pattern,
        priority=priority
    ) 