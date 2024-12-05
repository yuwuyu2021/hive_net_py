"""
HiveNet 客户端事件系统
"""
import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union, Tuple
from weakref import WeakSet

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """事件优先级"""
    HIGHEST = auto()  # 最高优先级
    HIGH = auto()     # 高优先级
    NORMAL = auto()   # 普通优先级
    LOW = auto()      # 低优先级
    LOWEST = auto()   # 最低优先级

@dataclass
class Event:
    """事件基类"""
    name: str  # 事件名称
    source: Any  # 事件源
    timestamp: float = field(default_factory=time.time)  # 事件时间戳
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    propagation_stopped: bool = False  # 是否停止传播

    def stop_propagation(self):
        """停止事件传播"""
        self.propagation_stopped = True

@dataclass
class ConnectionEvent(Event):
    """连接事件"""
    connection_id: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None

@dataclass
class MessageEvent(Event):
    """消息事件"""
    message_id: Optional[str] = None
    content: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None

@dataclass
class StateChangeEvent(Event):
    """状态变更事件"""
    old_state: Any = None
    new_state: Any = None
    reason: Optional[str] = None

@dataclass
class ErrorEvent(Event):
    """错误事件"""
    error: Optional[Exception] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None

class EventHandler:
    """事件处理器"""
    
    def __init__(self, callback: Callable, priority: EventPriority = EventPriority.NORMAL):
        self.callback = callback
        self.priority = priority
        self.is_async = asyncio.iscoroutinefunction(callback)

class EventDispatcher:
    """事件分发器"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Tuple[Callable, EventPriority]]] = {}
    
    def add_listener(self, event_name: str, callback: Callable,
                    priority: EventPriority = EventPriority.NORMAL):
        """添加事件监听器"""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        
        # 按优先级插入
        listeners = self._listeners[event_name]
        index = 0
        for i, (_, p) in enumerate(listeners):
            if p.value > priority.value:
                index = i
                break
        listeners.insert(index, (callback, priority))
    
    def remove_listener(self, event_name: str, callback: Callable):
        """移除事件监听器"""
        if event_name in self._listeners:
            self._listeners[event_name] = [
                (cb, p) for cb, p in self._listeners[event_name]
                if cb != callback
            ]
    
    async def dispatch(self, event: Event):
        """分发事件"""
        # 收集所有匹配的监听器
        matched_listeners = []
        
        # 处理通配符监听器
        if '*' in self._listeners:
            matched_listeners.extend(self._listeners['*'])
        
        # 处理具体事件监听器
        if event.name in self._listeners:
            matched_listeners.extend(self._listeners[event.name])
        
        # 处理通配符模式匹配
        for pattern, listeners in self._listeners.items():
            if pattern != '*' and pattern.endswith('*'):
                prefix = pattern[:-1]
                if event.name.startswith(prefix):
                    matched_listeners.extend(listeners)
        
        # 按优先级排序
        matched_listeners.sort(key=lambda x: x[1].value, reverse=True)
        
        # 调用监听器
        for callback, _ in matched_listeners:
            if event.propagation_stopped:
                break
            
            if inspect.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
    
    def _match_pattern(self, event_name: str, pattern: str) -> bool:
        """匹配事件名称和模式"""
        if pattern == '*':
            return True
        
        if pattern.endswith('.*'):
            prefix = pattern[:-2]
            return event_name.startswith(prefix + '.')
        
        return event_name == pattern

class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._dispatcher = EventDispatcher()
    
    def attach(self, dispatcher: EventDispatcher):
        """添加分发器"""
        self._dispatcher = dispatcher
        logger.debug("添加事件分发器")
    
    def detach(self, dispatcher: EventDispatcher):
        """移除分发器"""
        if self._dispatcher == dispatcher:
            self._dispatcher = EventDispatcher()
        logger.debug("移除事件分发器")
    
    async def publish(self, event: Event):
        """发布事件"""
        await self._dispatcher.dispatch(event)
    
    def subscribe(self, event_name: str, callback: Callable,
                 priority: EventPriority = EventPriority.NORMAL):
        """订阅事件"""
        self._dispatcher.add_listener(event_name, callback, priority)
        logger.debug(f"订阅事件: {event_name}")
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """取消订阅事件"""
        self._dispatcher.remove_listener(event_name, callback)
        logger.debug(f"取消订阅事件: {event_name}")

def event_listener(event_name: str, priority: EventPriority = EventPriority.NORMAL):
    """事件监听器装器"""
    def decorator(func):
        # 标记函数为事件监听器
        setattr(func, '_event_listener', True)
        setattr(func, '_event_name', event_name)
        setattr(func, '_event_priority', priority)
        return func
    return decorator

class EventSubscriber:
    """事件订阅者基类"""
    
    def __init__(self, dispatcher: EventDispatcher):
        self.dispatcher = dispatcher
        self._register_listeners()
    
    def _register_listeners(self):
        """注册所有标记为事件监听器的方法"""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '_event_listener'):
                event_name = getattr(method, '_event_name')
                priority = getattr(method, '_event_priority')
                self.dispatcher.add_listener(event_name, method, priority)
    
    def unsubscribe(self):
        """取消订阅所有事件"""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '_event_listener'):
                event_name = getattr(method, '_event_name')
                self.dispatcher.remove_listener(event_name, method)

# 预定义事件名称
class EventNames:
    """预定义事件称"""
    # 连接事件
    CONNECT = "connection.connect"
    DISCONNECT = "connection.disconnect"
    RECONNECT = "connection.reconnect"
    
    # 消息事件
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    MESSAGE_FILTERED = "message.filtered"
    MESSAGE_QUEUED = "message.queued"
    
    # 状态事件
    STATE_CHANGED = "state.changed"
    
    # 错误事件
    ERROR = "error"
    ERROR_HANDLER = "error.handler"
    ERROR_CONNECTION = "error.connection"
    ERROR_MESSAGE = "error.message"
    
    # 性能事件
    PERFORMANCE_WARNING = "performance.warning"
    PERFORMANCE_CRITICAL = "performance.critical"
    
    # 资源事件
    RESOURCE_WARNING = "resource.warning"
    RESOURCE_CRITICAL = "resource.critical" 