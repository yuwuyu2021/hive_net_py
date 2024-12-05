#!/usr/bin/env python3
"""
HiveNet 连接测试脚本
"""
import sys
import asyncio
import logging
from pathlib import Path
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hive_net_py.client.core.client import HiveClient, ClientState, ConnectionConfig
from hive_net_py.client.core.message_queue import QueueConfig

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection(host: str, port: int, num_clients: int = 1):
    """测试连接
    
    Args:
        host: 服务器地址
        port: 服务器端口
        num_clients: 客户端数量
    """
    clients = []
    
    try:
        # 创建多个客户端
        for i in range(num_clients):
            # 创建连接配置
            conn_config = ConnectionConfig(
                host=host,
                port=port,
                timeout=5.0,
                retry_interval=1.0,
                max_retries=2
            )
            
            # 创建队列配置
            queue_config = QueueConfig(
                max_size=100,
                batch_size=10,
                flush_interval=0.1
            )
            
            # 创建客户端
            client = HiveClient(
                connection_config=conn_config,
                queue_config=queue_config
            )
            clients.append(client)
            
            # 启动客户端
            await client.start()
            logger.info(f"客户端 {id(client)} 已启动")
            
            # 连接服务器
            logger.info(f"客户端 {id(client)} 正在连接服务器...")
            await client.connect()
            
            if client.state == ClientState.CONNECTED:
                logger.info(f"客户端 {id(client)} 连接成功")
                
                # 发送测试消息
                test_message = {
                    "type": "test",
                    "content": f"Hello from client {id(client)}"
                }
                await client.send_message(test_message)
                logger.info(f"客户端 {id(client)} 发送消息: {test_message}")
            else:
                logger.error(f"客户端 {id(client)} 连接失败")
        
        # 保持连接一段时间
        await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"测试过程出错: {e}")
    finally:
        # 断开所有客户端
        for client in clients:
            try:
                await client.disconnect()
                await client.stop()
                logger.info(f"客户端 {id(client)} 已断开连接并停止")
            except Exception as e:
                logger.error(f"断开客户端 {id(client)} 失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HiveNet 连接测试")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,  # 修改为默认的8080端口
        help="服务器端口 (默认: 8080)"
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=1,
        help="客户端数量 (默认: 1)"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(test_connection(args.host, args.port, args.num_clients))
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 