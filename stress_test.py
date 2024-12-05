#!/usr/bin/env python3
"""
HiveNet 压力测试脚本
"""
import sys
import asyncio
import logging
import time
import psutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hive_net_py.client.core.client import HiveClient, ClientState, ConnectionConfig
from hive_net_py.client.core.message_queue import QueueConfig

# 设置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            log_dir / f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)

class StressTest:
    """压力测试类"""
    
    def __init__(
        self,
        host: str,
        port: int,
        total_clients: int,
        batch_size: int,
        message_interval: float,
        test_duration: int
    ):
        """初始化压力测试
        
        Args:
            host: 服务器地址
            port: 服务器端口
            total_clients: 总客户端数量
            batch_size: 每批创建的客户端数量
            message_interval: 消息发送间隔（秒）
            test_duration: 测试持续时间（秒）
        """
        self.host = host
        self.port = port
        self.total_clients = total_clients
        self.batch_size = batch_size
        self.message_interval = message_interval
        self.test_duration = test_duration
        
        self.clients: List[HiveClient] = []
        self.stats = {
            "start_time": 0.0,
            "end_time": 0.0,
            "total_messages": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "connected_clients": 0,
            "failed_clients": 0,
            "avg_connect_time": 0.0,
            "avg_message_time": 0.0,
            "peak_memory": 0,
            "peak_cpu": 0.0
        }
        
        # 性能监控数据
        self.memory_usage = []
        self.cpu_usage = []
        self.connect_times = []
        self.message_times = []
    
    async def create_client(self) -> HiveClient:
        """创建客户端"""
        conn_config = ConnectionConfig(
            host=self.host,
            port=self.port,
            timeout=5.0,
            retry_interval=1.0,
            max_retries=2
        )
        
        queue_config = QueueConfig(
            max_size=100,
            batch_size=10,
            flush_interval=0.1
        )
        
        client = HiveClient(
            connection_config=conn_config,
            queue_config=queue_config
        )
        return client
    
    async def connect_clients(self, num_clients: int):
        """连接一批客户端
        
        Args:
            num_clients: 客户端数量
        """
        tasks = []
        for _ in range(num_clients):
            client = await self.create_client()
            self.clients.append(client)
            
            # 启动客户端
            await client.start()
            
            # 创建连接任务
            connect_time = time.time()
            task = asyncio.create_task(self._connect_client(client, connect_time))
            tasks.append(task)
        
        # 等待所有连接完成
        await asyncio.gather(*tasks)
    
    async def _connect_client(self, client: HiveClient, start_time: float):
        """连接单个客户端"""
        try:
            await client.connect()
            if client.state == ClientState.CONNECTED:
                self.stats["connected_clients"] += 1
                connect_time = time.time() - start_time
                self.connect_times.append(connect_time)
                logger.debug(f"客户端 {id(client)} 连接成功，耗时: {connect_time:.3f}秒")
            else:
                self.stats["failed_clients"] += 1
                logger.warning(f"客户端 {id(client)} 连接失败")
        except Exception as e:
            self.stats["failed_clients"] += 1
            logger.error(f"客户端 {id(client)} 连接出错: {e}")
    
    async def send_test_messages(self):
        """发送测试消息"""
        while time.time() - self.stats["start_time"] < self.test_duration:
            tasks = []
            for client in self.clients:
                if client.state == ClientState.CONNECTED:
                    task = asyncio.create_task(self._send_message(client))
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(self.message_interval)
    
    async def _send_message(self, client: HiveClient):
        """发送单条消息"""
        try:
            self.stats["total_messages"] += 1
            start_time = time.time()
            
            test_message = {
                "type": "test",
                "content": f"Test message from {id(client)}",
                "timestamp": start_time
            }
            await client.send_message(test_message)
            
            message_time = time.time() - start_time
            self.message_times.append(message_time)
            self.stats["successful_messages"] += 1
            logger.debug(f"客户端 {id(client)} 发送消息成功，耗时: {message_time:.3f}秒")
        except Exception as e:
            self.stats["failed_messages"] += 1
            logger.error(f"客户端 {id(client)} 发送消息失败: {e}")
    
    def update_performance_stats(self):
        """更新性能统计"""
        process = psutil.Process()
        memory_percent = process.memory_percent()
        cpu_percent = process.cpu_percent()
        
        self.memory_usage.append(memory_percent)
        self.cpu_usage.append(cpu_percent)
        
        self.stats["peak_memory"] = max(self.stats["peak_memory"], memory_percent)
        self.stats["peak_cpu"] = max(self.stats["peak_cpu"], cpu_percent)
    
    async def run(self):
        """运行压力测试"""
        logger.info(f"开始压力测试 - 目标: {self.total_clients} 个客户端")
        self.stats["start_time"] = time.time()
        
        try:
            # 分批创建并连接客户端
            remaining_clients = self.total_clients
            while remaining_clients > 0:
                batch_count = min(remaining_clients, self.batch_size)
                logger.info(f"创建第 {len(self.clients) + 1} 到 {len(self.clients) + batch_count} 个客户端")
                await self.connect_clients(batch_count)
                remaining_clients -= batch_count
                
                # 更新性能统计
                self.update_performance_stats()
            
            logger.info(f"所有客户端创建完成，开始发送测试消息")
            
            # 发送测试消息
            await self.send_test_messages()
            
        except Exception as e:
            logger.error(f"测试过程出错: {e}")
        finally:
            # 断开所有客户端
            disconnect_tasks = []
            for client in self.clients:
                task = asyncio.create_task(self._disconnect_client(client))
                disconnect_tasks.append(task)
            
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks)
            
            self.stats["end_time"] = time.time()
            
            # 计算平均值
            if self.connect_times:
                self.stats["avg_connect_time"] = sum(self.connect_times) / len(self.connect_times)
            if self.message_times:
                self.stats["avg_message_time"] = sum(self.message_times) / len(self.message_times)
            
            # 输出测试报告
            self.print_report()
    
    async def _disconnect_client(self, client: HiveClient):
        """断开单个客户端"""
        try:
            await client.disconnect()
            await client.stop()
            logger.debug(f"客户端 {id(client)} 已断开连接")
        except Exception as e:
            logger.error(f"断开客户端 {id(client)} 失败: {e}")
    
    def print_report(self):
        """打印测试报告"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        
        report = [
            "\n========== 压力测试报告 ==========",
            f"测试持续时间: {duration:.2f} 秒",
            f"目标客户端数: {self.total_clients}",
            f"成功连接数: {self.stats['connected_clients']}",
            f"连接失败数: {self.stats['failed_clients']}",
            f"平均连接时间: {self.stats['avg_connect_time']:.3f} 秒",
            f"总消息数: {self.stats['total_messages']}",
            f"成功消息数: {self.stats['successful_messages']}",
            f"失败消息数: {self.stats['failed_messages']}",
            f"平均消息时间: {self.stats['avg_message_time']:.3f} 秒",
            f"每秒消息数: {self.stats['successful_messages'] / duration:.2f}",
            f"内存峰值: {self.stats['peak_memory']:.1f}%",
            f"CPU峰值: {self.stats['peak_cpu']:.1f}%",
            "================================"
        ]
        
        logger.info("\n".join(report))

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HiveNet 压力测试")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="服务器端口 (默认: 8080)"
    )
    parser.add_argument(
        "--clients",
        type=int,
        default=100,
        help="总客户端数量 (默认: 100)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="每批创建的客户端数量 (默认: 10)"
    )
    parser.add_argument(
        "--message-interval",
        type=float,
        default=1.0,
        help="消息发送间隔，单位秒 (默认: 1.0)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="测试持续时间，单位秒 (默认: 60)"
    )
    
    args = parser.parse_args()
    
    # 创建并运行压力测试
    test = StressTest(
        host=args.host,
        port=args.port,
        total_clients=args.clients,
        batch_size=args.batch_size,
        message_interval=args.message_interval,
        test_duration=args.duration
    )
    
    try:
        await test.run()
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main()) 