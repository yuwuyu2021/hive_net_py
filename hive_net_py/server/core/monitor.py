"""
服务器性能监控模块
"""
import psutil
import time
import logging
import asyncio
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标数据"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int
    network_sent: int
    network_recv: int
    connections: int
    threads: int
    processes: int

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, history_size: int = 3600):
        """
        初始化性能监控器
        
        Args:
            history_size: 历史数据保存数量（默认1小时，每秒一个数据点）
        """
        self._history_size = history_size
        self._metrics_history: deque[SystemMetrics] = deque(maxlen=history_size)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._interval = 1.0  # 采集间隔（秒）
        self._callbacks: List[Callable[[SystemMetrics], None]] = []
        
        # 初始化网络计数器
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = time.time()
        
        # 初始化统计数据
        self._stats = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'network_rx_bytes': 0.0,
            'network_tx_bytes': 0.0,
            'current_connections': 0,
            'total_connections': 0
        }
    
    def add_callback(self, callback: Callable[[SystemMetrics], None]):
        """添加回调函数，当有新的指标数据时调用"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[SystemMetrics], None]):
        """移除回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def start(self):
        """启动监控"""
        if self._running:
            return
            
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("性能监控已启动")
    
    async def stop(self):
        """停止监控"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("性能监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                metrics = self._collect_metrics()
                self._metrics_history.append(metrics)
                
                # 更新统计数据
                self._stats.update({
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'network_rx_bytes': metrics.network_recv,
                    'network_tx_bytes': metrics.network_sent,
                    'current_connections': metrics.connections
                })
                
                # 调用回调函数
                for callback in self._callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"性能监控回调函数出错: {e}")
                
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"性能监控出错: {e}")
                await asyncio.sleep(1)
    
    def _collect_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        now = time.time()
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent()
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 网络IO
        net_io = psutil.net_io_counters()
        time_diff = now - self._last_net_time
        sent_speed = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_diff
        recv_speed = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_diff
        self._last_net_io = net_io
        self._last_net_time = now
        
        # 连接数
        connections = len(psutil.net_connections())
        
        # 线程和进程数
        threads = psutil.Process().num_threads()
        processes = len(psutil.pids())
        
        return SystemMetrics(
            timestamp=now,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used=memory.used,
            memory_total=memory.total,
            disk_percent=disk.percent,
            disk_used=disk.used,
            disk_total=disk.total,
            network_sent=int(sent_speed),
            network_recv=int(recv_speed),
            connections=connections,
            threads=threads,
            processes=processes
        )
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前指标"""
        if not self._metrics_history:
            return None
        return self._metrics_history[-1]
    
    def get_metrics_history(self) -> List[SystemMetrics]:
        """获取历史指标数据"""
        return list(self._metrics_history)
    
    def get_average_metrics(self, seconds: int = 60) -> Optional[SystemMetrics]:
        """获取指定时间段的平均指标
        
        Args:
            seconds: 时间段（秒）
            
        Returns:
            平均指标数据
        """
        if not self._metrics_history:
            return None
            
        # 获取指定时间段的数据
        now = time.time()
        recent_metrics = [
            m for m in self._metrics_history
            if now - m.timestamp <= seconds
        ]
        
        if not recent_metrics:
            return None
        
        # 计算平均值
        count = len(recent_metrics)
        return SystemMetrics(
            timestamp=now,
            cpu_percent=sum(m.cpu_percent for m in recent_metrics) / count,
            memory_percent=sum(m.memory_percent for m in recent_metrics) / count,
            memory_used=sum(m.memory_used for m in recent_metrics) // count,
            memory_total=recent_metrics[0].memory_total,
            disk_percent=sum(m.disk_percent for m in recent_metrics) / count,
            disk_used=sum(m.disk_used for m in recent_metrics) // count,
            disk_total=recent_metrics[0].disk_total,
            network_sent=sum(m.network_sent for m in recent_metrics) // count,
            network_recv=sum(m.network_recv for m in recent_metrics) // count,
            connections=sum(m.connections for m in recent_metrics) // count,
            threads=sum(m.threads for m in recent_metrics) // count,
            processes=sum(m.processes for m in recent_metrics) // count
        )
    
    def get_metrics_summary(self) -> Dict[str, float]:
        """获取性能指标摘要"""
        current = self.get_current_metrics()
        if not current:
            return {}
            
        avg_1min = self.get_average_metrics(60)
        avg_5min = self.get_average_metrics(300)
        
        return {
            "cpu_current": current.cpu_percent,
            "cpu_1min": avg_1min.cpu_percent if avg_1min else 0,
            "cpu_5min": avg_5min.cpu_percent if avg_5min else 0,
            "memory_current": current.memory_percent,
            "memory_1min": avg_1min.memory_percent if avg_1min else 0,
            "memory_5min": avg_5min.memory_percent if avg_5min else 0,
            "disk_current": current.disk_percent,
            "network_sent": current.network_sent,
            "network_recv": current.network_recv,
            "connections": current.connections
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计数据
        
        Returns:
            性能统计数据字典
        """
        return self._stats.copy()
    
    def update_connection_stats(self, current: int, total: int):
        """更新连接统计
        
        Args:
            current: 当前连接数
            total: 总连接数
        """
        self._stats['current_connections'] = current
        self._stats['total_connections'] = total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        """更新磁盘统计
        
        Args:
            disk_percent: 磁盘使用率
            disk_used: 已使用磁盘
            disk_total: 总磁盘
        """
        self._stats['disk_percent'] = disk_percent
        self._stats['disk_used'] = disk_used
        self._stats['disk_total'] = disk_total
    
    def update_network_stats(self, rx_bytes: int, tx_bytes: int):
        """更新网络统计
        
        Args:
            rx_bytes: 接收的字节数
            tx_bytes: 发送的字节数
        """
        self._stats['network_rx_bytes'] += rx_bytes
        self._stats['network_tx_bytes'] += tx_bytes
    
    def update_cpu_stats(self, cpu_percent: float):
        """更新CPU统计
        
        Args:
            cpu_percent: CPU使用率
        """
        self._stats['cpu_percent'] = cpu_percent
    
    def update_memory_stats(self, memory_percent: float, memory_used: int, memory_total: int):
        """更新内存统计
        
        Args:
            memory_percent: 内存使用率
            memory_used: 已使用内存
            memory_total: 总内存
        """
        self._stats['memory_percent'] = memory_percent
        self._stats['memory_used'] = memory_used
        self._stats['memory_total'] = memory_total
    
    def update_disk_stats(self, disk_percent: float, disk_used: int, disk_total: int):
        self.stats['current_connections'] = current
        self.stats['total_connections'] = total 