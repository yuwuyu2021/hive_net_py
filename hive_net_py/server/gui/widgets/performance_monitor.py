"""
性能监控组件
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QGroupBox
)
from PyQt6.QtCore import Qt

class PerformanceMonitor(QWidget):
    """性能监控组件类"""
    
    def __init__(self, parent=None):
        """初始化性能监控组件"""
        super().__init__(parent)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # CPU使用率
        cpu_group = QGroupBox("CPU使用率")
        cpu_layout = QHBoxLayout(cpu_group)
        
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_value = QLabel("0%")
        
        cpu_layout.addWidget(self.cpu_progress)
        cpu_layout.addWidget(self.cpu_value)
        layout.addWidget(cpu_group)
        
        # 内存使用率
        memory_group = QGroupBox("内存使用率")
        memory_layout = QHBoxLayout(memory_group)
        
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        self.memory_value = QLabel("0%")
        
        memory_layout.addWidget(self.memory_progress)
        memory_layout.addWidget(self.memory_value)
        layout.addWidget(memory_group)
        
        # 网络流量
        network_group = QGroupBox("网络流量")
        network_layout = QVBoxLayout(network_group)
        
        # 接收速率
        rx_layout = QHBoxLayout()
        rx_label = QLabel("接收速率:")
        self.rx_value = QLabel("0 B/s")
        rx_layout.addWidget(rx_label)
        rx_layout.addWidget(self.rx_value)
        rx_layout.addStretch()
        network_layout.addLayout(rx_layout)
        
        # 发送速率
        tx_layout = QHBoxLayout()
        tx_label = QLabel("发送速率:")
        self.tx_value = QLabel("0 B/s")
        tx_layout.addWidget(tx_label)
        tx_layout.addWidget(self.tx_value)
        tx_layout.addStretch()
        network_layout.addLayout(tx_layout)
        
        layout.addWidget(network_group)
        
        # 连接数
        connections_group = QGroupBox("连接统计")
        connections_layout = QVBoxLayout(connections_group)
        
        # 当前连接数
        current_layout = QHBoxLayout()
        current_label = QLabel("当前连接:")
        self.current_value = QLabel("0")
        current_layout.addWidget(current_label)
        current_layout.addWidget(self.current_value)
        current_layout.addStretch()
        connections_layout.addLayout(current_layout)
        
        # 历史连接数
        total_layout = QHBoxLayout()
        total_label = QLabel("历史连接:")
        self.total_value = QLabel("0")
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_value)
        total_layout.addStretch()
        connections_layout.addLayout(total_layout)
        
        layout.addWidget(connections_group)
        
        # 添加弹性空间
        layout.addStretch()
    
    def _format_bytes(self, bytes_value: float) -> str:
        """格式化字节数"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        return f"{bytes_value:.1f} {units[unit_index]}/s"
    
    def update_stats(self, stats: dict):
        """更新性能统计信息
        
        Args:
            stats: 性能统计数据字典
        """
        # 更新CPU使用率
        cpu_percent = stats.get('cpu_percent', 0)
        self.cpu_progress.setValue(int(cpu_percent))
        self.cpu_value.setText(f"{cpu_percent:.1f}%")
        
        # 更新内存使用率
        memory_percent = stats.get('memory_percent', 0)
        self.memory_progress.setValue(int(memory_percent))
        self.memory_value.setText(f"{memory_percent:.1f}%")
        
        # 更新网络流量
        rx_bytes = stats.get('network_rx_bytes', 0)
        tx_bytes = stats.get('network_tx_bytes', 0)
        self.rx_value.setText(self._format_bytes(rx_bytes))
        self.tx_value.setText(self._format_bytes(tx_bytes))
        
        # 更新连接数
        current_connections = stats.get('current_connections', 0)
        total_connections = stats.get('total_connections', 0)
        self.current_value.setText(str(current_connections))
        self.total_value.setText(str(total_connections)) 