"""
测试网络通信组件
"""
import asyncio
import json
import time
import pytest
from typing import Optional

from hive_net_py.common.network.base import MessageHandler, NetworkConnection
from hive_net_py.common.protocol import Message, MessageType

class TestMessageHandler(MessageHandler):
    """测试用消息处理器"""
    
    async def handle_connect(self, message: Message) -> Optional[Message]:
        """处理连接消息"""
        return Message(
            type=MessageType.CONNECT,
            payload={"status": "connected"},
            sequence=1,
            timestamp=time.time(),
            source_id="server",
            target_id=message.source_id
        )

class MockStreamReader:
    """模拟StreamReader"""
    def __init__(self, messages):
        self.messages = messages
        self.index = 0
    
    async def readline(self):
        """模拟读取一行数据"""
        if self.index >= len(self.messages):
            return b""
        message = self.messages[self.index]
        self.index += 1
        return json.dumps(message.to_dict()).encode('utf-8') + b'\n'

class MockStreamWriter:
    """模拟StreamWriter"""
    def __init__(self):
        self.written_data = []
        self.closed = False
    
    def write(self, data):
        """模拟写入数据"""
        self.written_data.append(data)
    
    async def drain(self):
        """模拟等待数据写入"""
        pass
    
    def close(self):
        """模拟关闭连接"""
        self.closed = True
    
    async def wait_closed(self):
        """模拟等待连接关闭"""
        pass

@pytest.mark.asyncio
async def test_network_connection():
    """测试网络连接"""
    # 准备测试数据
    test_message = Message(
        type=MessageType.CONNECT,
        payload={"client_id": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client"
    )
    
    # 创建模拟的流对象
    reader = MockStreamReader([test_message])
    writer = MockStreamWriter()
    handler = TestMessageHandler()
    
    # 创建网络连接
    connection = NetworkConnection(reader, writer, handler)
    
    # 测试发送消息
    await connection.send_message(test_message)
    assert len(writer.written_data) == 1
    sent_data = json.loads(writer.written_data[0].decode('utf-8').strip())
    assert sent_data['type'] == test_message.type.name
    
    # 测试接收消息
    received_message = await connection.receive_message()
    assert received_message is not None
    assert received_message.type == test_message.type
    assert received_message.payload == test_message.payload
    
    # 测试连接关闭
    await connection.close()
    assert writer.closed
    assert not connection.connected

@pytest.mark.asyncio
async def test_message_handler():
    """测试消息处理器"""
    handler = TestMessageHandler()
    
    # 测试处理连接消息
    test_message = Message(
        type=MessageType.CONNECT,
        payload={"client_id": "test"},
        sequence=1,
        timestamp=time.time(),
        source_id="client"
    )
    
    response = await handler.handle_message(test_message)
    assert response is not None
    assert response.type == MessageType.CONNECT
    assert response.payload["status"] == "connected"
    assert response.target_id == test_message.source_id
    
    # 测试处理未知消息类型
    unknown_message = Message(
        type=MessageType.ERROR,
        payload={},
        sequence=2,
        timestamp=time.time(),
        source_id="client"
    )
    
    response = await handler.handle_message(unknown_message)
    assert response is None 