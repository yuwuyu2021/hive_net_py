"""
HiveNet 客户端事件持久化
"""
import asyncio
import json
import logging
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .events import Event, ConnectionEvent, MessageEvent, StateChangeEvent, ErrorEvent

logger = logging.getLogger(__name__)

class EventStore(ABC):
    """事件存储接口"""
    
    @abstractmethod
    async def store_event(self, event: Event):
        """存储事件"""
        pass
    
    @abstractmethod
    async def get_events(self, start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        event_types: Optional[List[str]] = None,
                        source_id: Optional[str] = None) -> List[Event]:
        """获取事件"""
        pass
    
    @abstractmethod
    async def clear_events(self, before_time: Optional[float] = None):
        """清除事件"""
        pass

class SQLiteEventStore(EventStore):
    """SQLite事件存储"""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.commit()
    
    async def store_event(self, event: Event):
        """存储事件"""
        try:
            event_data = {
                'name': event.name,
                'event_type': event.__class__.__name__,
                'source': str(event.source),
                'timestamp': event.timestamp,
                'data': json.dumps(asdict(event))
            }
            
            # 使用线程池执行数据库操作
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_event_sync,
                event_data
            )
        except Exception as e:
            logger.error(f"存储事件失败: {e}")
    
    def _store_event_sync(self, event_data: Dict[str, Any]):
        """同步存储事件"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (name, event_type, source, timestamp, data)
                VALUES (:name, :event_type, :source, :timestamp, :data)
            """, event_data)
            conn.commit()
    
    async def get_events(self, start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        event_types: Optional[List[str]] = None,
                        source_id: Optional[str] = None) -> List[Event]:
        """获取事件"""
        try:
            # 构建查询条件
            conditions = []
            params = {}
            
            if start_time is not None:
                conditions.append("timestamp >= :start_time")
                params['start_time'] = start_time
            
            if end_time is not None:
                conditions.append("timestamp <= :end_time")
                params['end_time'] = end_time
            
            if event_types:
                conditions.append("event_type IN (%s)" % ','.join(['?'] * len(event_types)))
                params.update(dict(enumerate(event_types)))
            
            if source_id is not None:
                conditions.append("source = :source_id")
                params['source_id'] = source_id
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 使用线程池执行查询
            rows = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_events_sync,
                where_clause,
                params
            )
            
            # 反序列化事件
            events = []
            for row in rows:
                event_data = json.loads(row[4])  # data column
                event_type = row[1]  # event_type column
                
                # 根据事件类型创建相应的事件对象
                event_class = {
                    'ConnectionEvent': ConnectionEvent,
                    'MessageEvent': MessageEvent,
                    'StateChangeEvent': StateChangeEvent,
                    'ErrorEvent': ErrorEvent,
                    'Event': Event
                }.get(event_type, Event)
                
                events.append(event_class(**event_data))
            
            return events
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return []
    
    def _get_events_sync(self, where_clause: str, params: Dict[str, Any]) -> List[tuple]:
        """同步获取事件"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, event_type, source, timestamp, data
                FROM events
                WHERE {where_clause}
                ORDER BY timestamp ASC
            """, params)
            return cursor.fetchall()
    
    async def clear_events(self, before_time: Optional[float] = None):
        """清除事件"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._clear_events_sync,
                before_time
            )
        except Exception as e:
            logger.error(f"清除事件失败: {e}")
    
    def _clear_events_sync(self, before_time: Optional[float]):
        """同步清除事件"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if before_time is not None:
                cursor.execute("DELETE FROM events WHERE timestamp < ?", (before_time,))
            else:
                cursor.execute("DELETE FROM events")
            conn.commit()

class JSONEventStore(EventStore):
    """JSON文件事件存储"""
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self._events: List[Dict[str, Any]] = []
        self._load_events()
    
    def _load_events(self):
        """加载事件"""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self._events = json.load(f)
        except Exception as e:
            logger.error(f"加载事件失败: {e}")
            self._events = []
    
    def _save_events(self):
        """保存事件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, indent=2)
        except Exception as e:
            logger.error(f"保存事件失败: {e}")
    
    async def store_event(self, event: Event):
        """存储事件"""
        try:
            event_data = {
                'name': event.name,
                'event_type': event.__class__.__name__,
                'source': str(event.source),
                'timestamp': event.timestamp,
                'data': asdict(event)
            }
            
            # 使用线程池执行文件操作
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._store_event_sync,
                event_data
            )
        except Exception as e:
            logger.error(f"存储事件失败: {e}")
    
    def _store_event_sync(self, event_data: Dict[str, Any]):
        """同步存储事件"""
        self._events.append(event_data)
        self._save_events()
    
    async def get_events(self, start_time: Optional[float] = None,
                        end_time: Optional[float] = None,
                        event_types: Optional[List[str]] = None,
                        source_id: Optional[str] = None) -> List[Event]:
        """获取事件"""
        try:
            # 使用线程池执行查询
            events = await asyncio.get_event_loop().run_in_executor(
                None,
                self._get_events_sync,
                start_time,
                end_time,
                event_types,
                source_id
            )
            return events
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return []
    
    def _get_events_sync(self, start_time: Optional[float],
                        end_time: Optional[float],
                        event_types: Optional[List[str]],
                        source_id: Optional[str]) -> List[Event]:
        """同步获取事件"""
        filtered_events = []
        
        for event_data in self._events:
            # 应用过滤条件
            if start_time is not None and event_data['timestamp'] < start_time:
                continue
            
            if end_time is not None and event_data['timestamp'] > end_time:
                continue
            
            if event_types and event_data['event_type'] not in event_types:
                continue
            
            if source_id is not None and event_data['source'] != source_id:
                continue
            
            # 创建事件对象
            event_type = event_data['event_type']
            event_class = {
                'ConnectionEvent': ConnectionEvent,
                'MessageEvent': MessageEvent,
                'StateChangeEvent': StateChangeEvent,
                'ErrorEvent': ErrorEvent,
                'Event': Event
            }.get(event_type, Event)
            
            filtered_events.append(event_class(**event_data['data']))
        
        return filtered_events
    
    async def clear_events(self, before_time: Optional[float] = None):
        """清除事件"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._clear_events_sync,
                before_time
            )
        except Exception as e:
            logger.error(f"清除事件失败: {e}")
    
    def _clear_events_sync(self, before_time: Optional[float]):
        """同步清除事件"""
        if before_time is not None:
            self._events = [
                event for event in self._events
                if event['timestamp'] >= before_time
            ]
        else:
            self._events.clear()
        self._save_events()

class EventReplay:
    """事件重放"""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self._handlers: Dict[str, List[Any]] = {}
    
    def register_handler(self, event_type: str, handler: Any):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: str, handler: Any):
        """注销事件处理器"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]
    
    async def replay_events(self, start_time: Optional[float] = None,
                          end_time: Optional[float] = None,
                          event_types: Optional[List[str]] = None,
                          source_id: Optional[str] = None,
                          speed: float = 1.0):
        """重放事件"""
        events = await self.event_store.get_events(
            start_time=start_time,
            end_time=end_time,
            event_types=event_types,
            source_id=source_id
        )
        
        if not events:
            return
        
        # 按时间戳排序
        events.sort(key=lambda e: e.timestamp)
        base_time = events[0].timestamp
        
        for event in events:
            # 计算等待时间
            wait_time = (event.timestamp - base_time) / speed
            await asyncio.sleep(max(0, wait_time))
            
            # 调用处理器
            event_type = event.__class__.__name__
            if event_type in self._handlers:
                for handler in self._handlers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"事件处理器出错: {e}")
            
            base_time = event.timestamp 