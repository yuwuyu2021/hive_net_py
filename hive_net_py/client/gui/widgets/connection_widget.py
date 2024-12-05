"""
连接管理界面
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ...core.client import ClientState


class ConnectionWidget(QWidget):
    """连接管理界面类"""
    
    # 信号定义
    connect_requested = pyqtSignal()
    disconnect_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        """初始化连接管理界面"""
        super().__init__(parent)
        
        # 当前状态
        self._current_state: Optional[ClientState] = None
        
        # 初始化UI
        self._init_ui()
        
        # 更新状态
        self.update_status(ClientState.DISCONNECTED)
    
    def _init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        
        # 状态组
        status_group = QGroupBox("连接状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态信息
        status_info_layout = QHBoxLayout()
        self.status_label = QLabel("状态:")
        self.status_value = QLabel("未连接")
        status_info_layout.addWidget(self.status_label)
        status_info_layout.addWidget(self.status_value)
        status_info_layout.addStretch()
        status_layout.addLayout(status_info_layout)
        
        # 连接信息
        connection_info_layout = QHBoxLayout()
        self.connection_label = QLabel("连接信息:")
        self.connection_value = QLabel("无")
        connection_info_layout.addWidget(self.connection_label)
        connection_info_layout.addWidget(self.connection_value)
        connection_info_layout.addStretch()
        status_layout.addLayout(connection_info_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("连接")
        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addStretch()
        status_layout.addLayout(button_layout)
        
        layout.addWidget(status_group)
        
        # 日志组
        log_group = QGroupBox("连接日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # 连接信号
        self.connect_button.clicked.connect(self._handle_connect)
        self.disconnect_button.clicked.connect(self._handle_disconnect)
    
    def _handle_connect(self):
        """处理连接请求"""
        self.add_log("正在连接服务器...")
        self.connect_requested.emit()
    
    def _handle_disconnect(self):
        """处理断开请求"""
        self.add_log("正在断开连接...")
        self.disconnect_requested.emit()
    
    def update_status(self, state: ClientState):
        """更新连接状态"""
        self._current_state = state
        
        # 更新状态显示
        status_messages = {
            ClientState.DISCONNECTED: "未连接",
            ClientState.CONNECTING: "正在连接...",
            ClientState.CONNECTED: "已连接",
            ClientState.AUTHENTICATING: "正在认证...",
            ClientState.AUTHENTICATED: "已认证",
            ClientState.ERROR: "连接错误"
        }
        self.status_value.setText(status_messages.get(state, "未知状态"))
        
        # 更新按钮状态
        self.connect_button.setEnabled(state in (ClientState.DISCONNECTED, ClientState.ERROR))
        self.disconnect_button.setEnabled(state not in (ClientState.DISCONNECTED, ClientState.ERROR))
        
        # 添加日志
        self.add_log(f"连接状态变更: {status_messages.get(state, '未知状态')}")
    
    def update_connection_info(self, host: str, port: int):
        """更新连接信息"""
        self.connection_value.setText(f"{host}:{port}")
    
    def add_log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear() 