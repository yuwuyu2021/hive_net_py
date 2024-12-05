"""
HiveNet 基础协议定义
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional

class MessageType(Enum):
    """消息类型枚举"""
    CONNECT = auto()      # 连接请求
    DISCONNECT = auto()   # 断开连接
    DATA = auto()         # 数据传输
    HEARTBEAT = auto()    # 心跳包
    ERROR = auto()        # 错误消息

@dataclass
class Message:
    """基础消息类"""
    type: MessageType
    payload: Dict[str, Any]
    sequence: int
    timestamp: float
    source_id: str
    target_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典格式"""
        return {
            'type': self.type.name,
            'payload': self.payload,
            'sequence': self.sequence,
            'timestamp': self.timestamp,
            'source_id': self.source_id,
            'target_id': self.target_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息对象"""
        return cls(
            type=MessageType[data['type']],
            payload=data['payload'],
            sequence=data['sequence'],
            timestamp=data['timestamp'],
            source_id=data['source_id'],
            target_id=data.get('target_id')
        ) 