"""
HiveNet 客户端消息过滤器
"""
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union

from ...common.protocol import Message, MessageType

logger = logging.getLogger(__name__)

class FilterAction(Enum):
    """过滤器动作"""
    ACCEPT = auto()  # 接受消息
    REJECT = auto()  # 拒绝消息
    MODIFY = auto()  # 修改消息

@dataclass
class FilterRule:
    """过滤规则"""
    name: str
    message_types: Set[MessageType] = field(default_factory=set)  # 消息类型匹配
    source_pattern: Optional[Pattern] = None  # 源ID匹配模式
    target_pattern: Optional[Pattern] = None  # 目标ID匹配模式
    payload_patterns: Dict[str, Union[str, Pattern, Any]] = field(default_factory=dict)  # 负载匹配模式
    action: FilterAction = FilterAction.ACCEPT  # 默认动作
    priority: int = 0  # 优先级，数字越大优先级越高
    modifier: Optional[Callable[[Message], Message]] = None  # 消息修改器

    def matches(self, message: Message) -> bool:
        """检查消息是否匹配规则"""
        # 检查消息类型
        if self.message_types and message.type not in self.message_types:
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
        for key, pattern in self.payload_patterns.items():
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

class MessageFilter(ABC):
    """消息过滤器基类"""
    
    @abstractmethod
    async def filter_message(self, message: Message) -> tuple[FilterAction, Optional[Message]]:
        """过滤消息"""
        pass

class RuleBasedFilter(MessageFilter):
    """基于规则的过滤器"""
    
    def __init__(self):
        self.rules: List[FilterRule] = []
    
    def add_rule(self, rule: FilterRule):
        """添加过滤规则"""
        self.rules.append(rule)
        # 按优先级排序规则
        self.rules.sort(key=lambda x: x.priority, reverse=True)
        logger.debug(f"添加过滤规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除过滤规则"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        logger.debug(f"移除过滤规则: {rule_name}")
    
    async def filter_message(self, message: Message) -> tuple[FilterAction, Optional[Message]]:
        """过滤消息"""
        for rule in self.rules:
            if rule.matches(message):
                logger.debug(f"消息匹配规则: {rule.name}")
                
                if rule.action == FilterAction.MODIFY and rule.modifier:
                    try:
                        modified_message = rule.modifier(message)
                        return FilterAction.MODIFY, modified_message
                    except Exception as e:
                        logger.error(f"修改消息时出错: {e}")
                        continue
                
                return rule.action, None
        
        # 默认接受消息
        return FilterAction.ACCEPT, None

def create_filter_rule(
    name: str,
    message_types: Optional[Set[MessageType]] = None,
    source_pattern: Optional[str] = None,
    target_pattern: Optional[str] = None,
    payload_patterns: Optional[Dict[str, Any]] = None,
    action: FilterAction = FilterAction.ACCEPT,
    priority: int = 0,
    modifier: Optional[Callable[[Message], Message]] = None
) -> FilterRule:
    """创建过滤规则的辅助函数"""
    # 处理消息类型
    message_types = message_types or set()
    
    # 处理模式
    source_pattern = re.compile(source_pattern) if source_pattern else None
    target_pattern = re.compile(target_pattern) if target_pattern else None
    
    # 处理负载模式
    processed_patterns = {}
    if payload_patterns:
        for key, pattern in payload_patterns.items():
            if isinstance(pattern, str) and any(c in pattern for c in r'.^$*+?{}[]|\()'):
                processed_patterns[key] = re.compile(pattern)
            else:
                processed_patterns[key] = pattern
    
    return FilterRule(
        name=name,
        message_types=message_types,
        source_pattern=source_pattern,
        target_pattern=target_pattern,
        payload_patterns=processed_patterns,
        action=action,
        priority=priority,
        modifier=modifier
    )

class CompositeFilter(MessageFilter):
    """组合过滤器"""
    
    def __init__(self):
        self.filters: List[MessageFilter] = []
    
    def add_filter(self, filter_: MessageFilter):
        """添加过滤器"""
        self.filters.append(filter_)
        logger.debug("添加过滤器")
    
    def remove_filter(self, filter_: MessageFilter):
        """移除过滤器"""
        self.filters.remove(filter_)
        logger.debug("移除过滤器")
    
    async def filter_message(self, message: Message) -> tuple[FilterAction, Optional[Message]]:
        """过滤消息"""
        current_message = message
        
        for filter_ in self.filters:
            action, modified_message = await filter_.filter_message(current_message)
            
            if action == FilterAction.REJECT:
                return FilterAction.REJECT, None
            elif action == FilterAction.MODIFY and modified_message:
                current_message = modified_message
        
        return FilterAction.ACCEPT, current_message 