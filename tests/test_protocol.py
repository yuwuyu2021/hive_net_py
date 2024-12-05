"""
测试基础协议功能
"""
import time
from hive_net_py.common.protocol import Message, MessageType

def test_message_creation():
    """测试消息创建"""
    msg = Message(
        type=MessageType.CONNECT,
        payload={'client_id': '123'},
        sequence=1,
        timestamp=time.time(),
        source_id='client_123'
    )
    assert msg.type == MessageType.CONNECT
    assert msg.payload['client_id'] == '123'
    assert msg.sequence == 1
    assert msg.source_id == 'client_123'
    assert msg.target_id is None

def test_message_serialization():
    """测试消息序列化"""
    timestamp = time.time()
    original_msg = Message(
        type=MessageType.DATA,
        payload={'data': 'test'},
        sequence=2,
        timestamp=timestamp,
        source_id='client_123',
        target_id='server_1'
    )
    
    # 转换为字典
    msg_dict = original_msg.to_dict()
    
    # 从字典重建消息
    restored_msg = Message.from_dict(msg_dict)
    
    # 验证字段
    assert restored_msg.type == original_msg.type
    assert restored_msg.payload == original_msg.payload
    assert restored_msg.sequence == original_msg.sequence
    assert restored_msg.timestamp == original_msg.timestamp
    assert restored_msg.source_id == original_msg.source_id
    assert restored_msg.target_id == original_msg.target_id

def test_message_types():
    """测试所有消息类型"""
    for msg_type in MessageType:
        msg = Message(
            type=msg_type,
            payload={},
            sequence=1,
            timestamp=time.time(),
            source_id='test'
        )
        assert msg.type == msg_type 