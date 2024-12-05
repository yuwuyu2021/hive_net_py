#!/usr/bin/env python3
"""
测试客户端
"""
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hive_net_py.client.core.client import HiveClient
from hive_net_py.common.config.base import ConnectionConfig

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    try:
        # 创建连接配置
        config = ConnectionConfig(
            host="localhost",
            port=8081,
            timeout=30,
            retry_count=3,
            retry_delay=1,
            keep_alive=True,
            buffer_size=8192
        )
        
        # 创建客户端
        client = HiveClient(config)
        
        # 连接服务器
        await client.connect()
        logger.info("已连接到服务器")
        
        # 发送测试消息
        await client.send("Hello, Server!")
        logger.info("已发送测试消息")
        
        # 等待响应
        response = await client.receive()
        logger.info(f"收到响应: {response}")
        
        # 断开连接
        await client.disconnect()
        logger.info("已断开连接")
        
    except Exception as e:
        logger.error(f"客户端运行出错: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main()) 