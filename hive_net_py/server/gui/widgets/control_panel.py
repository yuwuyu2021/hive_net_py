"""
服务器控制面板组件
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QComboBox,
    QGroupBox,
    QCheckBox
)
from PyQt6.QtCore import Qt

class ControlPanel(QWidget):
    """控制面板组件类"""
    
    def __init__(self, parent=None):
        """初始化控制面板"""
        super().__init__(parent)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 服务器设置
        settings_group = QGroupBox("服务器设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 性能设置
        performance_layout = QHBoxLayout()
        
        # 线程池大小
        thread_label = QLabel("线程池大小:")
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 100)
        self.thread_spin.setValue(10)
        performance_layout.addWidget(thread_label)
        performance_layout.addWidget(self.thread_spin)
        
        # 最大连接数
        connections_label = QLabel("最大连接数:")
        self.connections_spin = QSpinBox()
        self.connections_spin.setRange(1, 10000)
        self.connections_spin.setValue(1000)
        performance_layout.addWidget(connections_label)
        performance_layout.addWidget(self.connections_spin)
        
        performance_layout.addStretch()
        settings_layout.addLayout(performance_layout)
        
        # 网络设置
        network_layout = QHBoxLayout()
        
        # 缓冲区大小
        buffer_label = QLabel("缓冲区大小:")
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(1024, 65536)
        self.buffer_spin.setValue(8192)
        self.buffer_spin.setSingleStep(1024)
        network_layout.addWidget(buffer_label)
        network_layout.addWidget(self.buffer_spin)
        
        # 超时时间
        timeout_label = QLabel("超时时间(秒):")
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 300)
        self.timeout_spin.setValue(30)
        network_layout.addWidget(timeout_label)
        network_layout.addWidget(self.timeout_spin)
        
        network_layout.addStretch()
        settings_layout.addLayout(network_layout)
        
        # 安全设置
        security_layout = QHBoxLayout()
        
        # SSL/TLS
        self.ssl_check = QCheckBox("启用SSL/TLS")
        security_layout.addWidget(self.ssl_check)
        
        # 认证
        self.auth_check = QCheckBox("启用认证")
        security_layout.addWidget(self.auth_check)
        
        security_layout.addStretch()
        settings_layout.addLayout(security_layout)
        
        layout.addWidget(settings_group)
        
        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QHBoxLayout(log_group)
        
        # 日志级别
        level_label = QLabel("日志级别:")
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL"
        ])
        self.level_combo.setCurrentText("INFO")
        log_layout.addWidget(level_label)
        log_layout.addWidget(self.level_combo)
        
        # 日志文件
        self.file_check = QCheckBox("启用日志文件")
        self.file_check.setChecked(True)
        log_layout.addWidget(self.file_check)
        
        log_layout.addStretch()
        layout.addWidget(log_group)
        
        # 监控设置
        monitor_group = QGroupBox("监控设置")
        monitor_layout = QHBoxLayout(monitor_group)
        
        # 监控间隔
        interval_label = QLabel("监控间隔(秒):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        monitor_layout.addWidget(interval_label)
        monitor_layout.addWidget(self.interval_spin)
        
        # 性能监控
        self.perf_check = QCheckBox("性能监控")
        self.perf_check.setChecked(True)
        monitor_layout.addWidget(self.perf_check)
        
        # 网络监控
        self.network_check = QCheckBox("网络监控")
        self.network_check.setChecked(True)
        monitor_layout.addWidget(self.network_check)
        
        monitor_layout.addStretch()
        layout.addWidget(monitor_group)
        
        # 添加弹性空间
        layout.addStretch()
    
    def get_settings(self) -> dict:
        """获取当前设置
        
        Returns:
            设置字典
        """
        return {
            # 性能设置
            'thread_pool_size': self.thread_spin.value(),
            'max_connections': self.connections_spin.value(),
            
            # 网络设置
            'buffer_size': self.buffer_spin.value(),
            'timeout': self.timeout_spin.value(),
            
            # 安全设置
            'enable_ssl': self.ssl_check.isChecked(),
            'enable_auth': self.auth_check.isChecked(),
            
            # 日志设置
            'log_level': self.level_combo.currentText(),
            'enable_log_file': self.file_check.isChecked(),
            
            # 监控设置
            'monitor_interval': self.interval_spin.value(),
            'enable_perf_monitor': self.perf_check.isChecked(),
            'enable_network_monitor': self.network_check.isChecked()
        }
    
    def apply_settings(self, settings: dict):
        """应用设置
        
        Args:
            settings: 设置字典
        """
        # 性能设置
        self.thread_spin.setValue(settings.get('thread_pool_size', 10))
        self.connections_spin.setValue(settings.get('max_connections', 1000))
        
        # 网络设置
        self.buffer_spin.setValue(settings.get('buffer_size', 8192))
        self.timeout_spin.setValue(settings.get('timeout', 30))
        
        # 安全设置
        self.ssl_check.setChecked(settings.get('enable_ssl', False))
        self.auth_check.setChecked(settings.get('enable_auth', False))
        
        # 日志设置
        self.level_combo.setCurrentText(settings.get('log_level', 'INFO'))
        self.file_check.setChecked(settings.get('enable_log_file', True))
        
        # 监控设置
        self.interval_spin.setValue(settings.get('monitor_interval', 5))
        self.perf_check.setChecked(settings.get('enable_perf_monitor', True))
        self.network_check.setChecked(settings.get('enable_network_monitor', True)) 