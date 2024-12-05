"""
设置对话框
"""
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QComboBox,
    QGroupBox,
    QMessageBox
)
from PyQt6.QtCore import Qt

from ...core.client import ConnectionConfig


class SettingsDialog(QDialog):
    """设置对话框类"""
    
    def __init__(self, parent=None):
        """初始化设置对话框"""
        super().__init__(parent)
        
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # 加载当前配置
        self._load_config()
        
        # 初始化UI
        self._init_ui()
        
        # 连接信号
        self._init_signals()
    
    def _load_config(self):
        """加载当前配置"""
        # TODO: 从配置文件加载
        self._config = {
            'connection': {
                'auto_reconnect': True,
                'reconnect_interval': 5,
                'max_retry': 3,
                'timeout': 30,
                'keep_alive': True,
                'keep_alive_interval': 60
            },
            'message': {
                'max_queue_size': 1000,
                'batch_size': 100,
                'compression': True
            },
            'event': {
                'max_events': 1000,
                'auto_clear': True,
                'clear_interval': 3600
            },
            'logging': {
                'level': 'INFO',
                'file_enabled': True,
                'file_path': 'logs/client.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            }
        }
    
    def _init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 连接设置
        connection_tab = QWidget()
        connection_layout = QVBoxLayout(connection_tab)
        
        # 自动重连
        reconnect_group = QGroupBox("自动重连")
        reconnect_layout = QVBoxLayout(reconnect_group)
        
        self.auto_reconnect = QCheckBox("启用自动重连")
        self.auto_reconnect.setChecked(self._config['connection']['auto_reconnect'])
        reconnect_layout.addWidget(self.auto_reconnect)
        
        interval_layout = QHBoxLayout()
        interval_label = QLabel("重连间隔(秒):")
        self.reconnect_interval = QSpinBox()
        self.reconnect_interval.setRange(1, 300)
        self.reconnect_interval.setValue(self._config['connection']['reconnect_interval'])
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.reconnect_interval)
        reconnect_layout.addLayout(interval_layout)
        
        retry_layout = QHBoxLayout()
        retry_label = QLabel("最大重试次数:")
        self.max_retry = QSpinBox()
        self.max_retry.setRange(0, 100)
        self.max_retry.setValue(self._config['connection']['max_retry'])
        retry_layout.addWidget(retry_label)
        retry_layout.addWidget(self.max_retry)
        reconnect_layout.addLayout(retry_layout)
        
        connection_layout.addWidget(reconnect_group)
        
        # 连接超时
        timeout_group = QGroupBox("连接超时")
        timeout_layout = QVBoxLayout(timeout_group)
        
        timeout_value_layout = QHBoxLayout()
        timeout_label = QLabel("超时时间(秒):")
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(self._config['connection']['timeout'])
        timeout_value_layout.addWidget(timeout_label)
        timeout_value_layout.addWidget(self.timeout)
        timeout_layout.addLayout(timeout_value_layout)
        
        connection_layout.addWidget(timeout_group)
        
        # 心跳设置
        keepalive_group = QGroupBox("心跳设置")
        keepalive_layout = QVBoxLayout(keepalive_group)
        
        self.keep_alive = QCheckBox("启用心跳")
        self.keep_alive.setChecked(self._config['connection']['keep_alive'])
        keepalive_layout.addWidget(self.keep_alive)
        
        keepalive_interval_layout = QHBoxLayout()
        keepalive_interval_label = QLabel("心跳间隔(秒):")
        self.keepalive_interval = QSpinBox()
        self.keepalive_interval.setRange(1, 300)
        self.keepalive_interval.setValue(self._config['connection']['keep_alive_interval'])
        keepalive_interval_layout.addWidget(keepalive_interval_label)
        keepalive_interval_layout.addWidget(self.keepalive_interval)
        keepalive_layout.addLayout(keepalive_interval_layout)
        
        connection_layout.addWidget(keepalive_group)
        
        tab_widget.addTab(connection_tab, "连接")
        
        # 消息设置
        message_tab = QWidget()
        message_layout = QVBoxLayout(message_tab)
        
        # 队列设置
        queue_group = QGroupBox("消息队列")
        queue_layout = QVBoxLayout(queue_group)
        
        queue_size_layout = QHBoxLayout()
        queue_size_label = QLabel("最大队列大小:")
        self.queue_size = QSpinBox()
        self.queue_size.setRange(100, 10000)
        self.queue_size.setValue(self._config['message']['max_queue_size'])
        queue_size_layout.addWidget(queue_size_label)
        queue_size_layout.addWidget(self.queue_size)
        queue_layout.addLayout(queue_size_layout)
        
        batch_size_layout = QHBoxLayout()
        batch_size_label = QLabel("批处理大小:")
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 1000)
        self.batch_size.setValue(self._config['message']['batch_size'])
        batch_size_layout.addWidget(batch_size_label)
        batch_size_layout.addWidget(self.batch_size)
        queue_layout.addLayout(batch_size_layout)
        
        self.compression = QCheckBox("启用压缩")
        self.compression.setChecked(self._config['message']['compression'])
        queue_layout.addWidget(self.compression)
        
        message_layout.addWidget(queue_group)
        
        tab_widget.addTab(message_tab, "消息")
        
        # 事件设置
        event_tab = QWidget()
        event_layout = QVBoxLayout(event_tab)
        
        # 事件存储
        event_storage_group = QGroupBox("事件存储")
        event_storage_layout = QVBoxLayout(event_storage_group)
        
        max_events_layout = QHBoxLayout()
        max_events_label = QLabel("最大事件数:")
        self.max_events = QSpinBox()
        self.max_events.setRange(100, 10000)
        self.max_events.setValue(self._config['event']['max_events'])
        max_events_layout.addWidget(max_events_label)
        max_events_layout.addWidget(self.max_events)
        event_storage_layout.addLayout(max_events_layout)
        
        self.auto_clear = QCheckBox("自动清理")
        self.auto_clear.setChecked(self._config['event']['auto_clear'])
        event_storage_layout.addWidget(self.auto_clear)
        
        clear_interval_layout = QHBoxLayout()
        clear_interval_label = QLabel("清理间隔(秒):")
        self.clear_interval = QSpinBox()
        self.clear_interval.setRange(60, 86400)
        self.clear_interval.setValue(self._config['event']['clear_interval'])
        clear_interval_layout.addWidget(clear_interval_label)
        clear_interval_layout.addWidget(self.clear_interval)
        event_storage_layout.addLayout(clear_interval_layout)
        
        event_layout.addWidget(event_storage_group)
        
        tab_widget.addTab(event_tab, "事件")
        
        # 日志设置
        logging_tab = QWidget()
        logging_layout = QVBoxLayout(logging_tab)
        
        # 日志级别
        level_layout = QHBoxLayout()
        level_label = QLabel("日志级别:")
        self.log_level = QComboBox()
        self.log_level.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.log_level.setCurrentText(self._config['logging']['level'])
        level_layout.addWidget(level_label)
        level_layout.addWidget(self.log_level)
        logging_layout.addLayout(level_layout)
        
        # 文件日志
        file_group = QGroupBox("文件日志")
        file_layout = QVBoxLayout(file_group)
        
        self.file_enabled = QCheckBox("启用文件日志")
        self.file_enabled.setChecked(self._config['logging']['file_enabled'])
        file_layout.addWidget(self.file_enabled)
        
        path_layout = QHBoxLayout()
        path_label = QLabel("日志文件:")
        self.file_path = QLineEdit(self._config['logging']['file_path'])
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.file_path)
        file_layout.addLayout(path_layout)
        
        size_layout = QHBoxLayout()
        size_label = QLabel("最大大小(MB):")
        self.max_size = QSpinBox()
        self.max_size.setRange(1, 1000)
        self.max_size.setValue(self._config['logging']['max_size'] // 1048576)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.max_size)
        file_layout.addLayout(size_layout)
        
        backup_layout = QHBoxLayout()
        backup_label = QLabel("备份数量:")
        self.backup_count = QSpinBox()
        self.backup_count.setRange(0, 100)
        self.backup_count.setValue(self._config['logging']['backup_count'])
        backup_layout.addWidget(backup_label)
        backup_layout.addWidget(self.backup_count)
        file_layout.addLayout(backup_layout)
        
        logging_layout.addWidget(file_group)
        
        tab_widget.addTab(logging_tab, "日志")
        
        layout.addWidget(tab_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def _init_signals(self):
        """初始化信号连接"""
        # 自动重连相关
        self.auto_reconnect.toggled.connect(
            lambda checked: self.reconnect_interval.setEnabled(checked)
        )
        self.auto_reconnect.toggled.connect(
            lambda checked: self.max_retry.setEnabled(checked)
        )
        
        # 心跳相关
        self.keep_alive.toggled.connect(
            lambda checked: self.keepalive_interval.setEnabled(checked)
        )
        
        # 文件日志相关
        self.file_enabled.toggled.connect(
            lambda checked: self.file_path.setEnabled(checked)
        )
        self.file_enabled.toggled.connect(
            lambda checked: self.max_size.setEnabled(checked)
        )
        self.file_enabled.toggled.connect(
            lambda checked: self.backup_count.setEnabled(checked)
        )
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置
        
        Returns:
            当前配置字典
        """
        return {
            'connection': {
                'auto_reconnect': self.auto_reconnect.isChecked(),
                'reconnect_interval': self.reconnect_interval.value(),
                'max_retry': self.max_retry.value(),
                'timeout': self.timeout.value(),
                'keep_alive': self.keep_alive.isChecked(),
                'keep_alive_interval': self.keepalive_interval.value()
            },
            'message': {
                'max_queue_size': self.queue_size.value(),
                'batch_size': self.batch_size.value(),
                'compression': self.compression.isChecked()
            },
            'event': {
                'max_events': self.max_events.value(),
                'auto_clear': self.auto_clear.isChecked(),
                'clear_interval': self.clear_interval.value()
            },
            'logging': {
                'level': self.log_level.currentText(),
                'file_enabled': self.file_enabled.isChecked(),
                'file_path': self.file_path.text(),
                'max_size': self.max_size.value() * 1024 * 1024,  # 转换为字节
                'backup_count': self.backup_count.value()
            }
        }
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置
        
        Args:
            config: 配置字典
        """
        # 连接设置
        conn_config = config.get('connection', {})
        self.auto_reconnect.setChecked(conn_config.get('auto_reconnect', True))
        self.reconnect_interval.setValue(conn_config.get('reconnect_interval', 5))
        self.max_retry.setValue(conn_config.get('max_retry', 3))
        self.timeout.setValue(conn_config.get('timeout', 30))
        self.keep_alive.setChecked(conn_config.get('keep_alive', True))
        self.keepalive_interval.setValue(conn_config.get('keep_alive_interval', 60))
        
        # 消息设置
        msg_config = config.get('message', {})
        self.queue_size.setValue(msg_config.get('max_queue_size', 1000))
        self.batch_size.setValue(msg_config.get('batch_size', 100))
        self.compression.setChecked(msg_config.get('compression', True))
        
        # 事件设置
        event_config = config.get('event', {})
        self.max_events.setValue(event_config.get('max_events', 1000))
        self.auto_clear.setChecked(event_config.get('auto_clear', True))
        self.clear_interval.setValue(event_config.get('clear_interval', 3600))
        
        # 日志设置
        log_config = config.get('logging', {})
        self.log_level.setCurrentText(log_config.get('level', 'INFO'))
        self.file_enabled.setChecked(log_config.get('file_enabled', True))
        self.file_path.setText(log_config.get('file_path', 'logs/client.log'))
        self.max_size.setValue(log_config.get('max_size', 10485760) // (1024 * 1024))  # 转换为MB
        self.backup_count.setValue(log_config.get('backup_count', 5))
    
    def accept(self):
        """确认对话框"""
        try:
            config = self.get_config()
            # TODO: 保存配置到文件
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
    
    def reject(self):
        """取消对话框"""
        reply = QMessageBox.question(
            self,
            "确认取消",
            "确定要放弃更改吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            super().reject()
    
    def get_config(self) -> Dict[str, Any]:
        """获取设置配置"""
        return self._config.copy() 