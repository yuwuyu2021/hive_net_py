"""
登录对话框模块
"""
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from PyQt6.QtCore import Qt

from ...core.client import ConnectionConfig

class LoginDialog(QDialog):
    """登录对话框类"""
    
    def __init__(self, parent=None):
        """初始化登录对话框"""
        super().__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("连接服务器")
        self.setModal(True)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 服务器地址
        host_layout = QHBoxLayout()
        host_label = QLabel("服务器地址:")
        self.host_edit = QLineEdit()
        self.host_edit.setText("localhost")
        host_layout.addWidget(host_label)
        host_layout.addWidget(self.host_edit)
        layout.addLayout(host_layout)
        
        # 端口
        port_layout = QHBoxLayout()
        port_label = QLabel("端口:")
        self.port_edit = QLineEdit()
        self.port_edit.setText("8080")
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_edit)
        layout.addLayout(port_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        connect_button = QPushButton("连接")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(connect_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        connect_button.clicked.connect(self._handle_connect)
        cancel_button.clicked.connect(self.reject)
    
    def _handle_connect(self):
        """处理连接按钮点击"""
        try:
            # 验证输入
            host = self.host_edit.text().strip()
            if not host:
                raise ValueError("服务器地址不能为空")
            
            port = int(self.port_edit.text().strip())
            if not (0 <= port <= 65535):
                raise ValueError("端口号必须在0-65535之间")
            
            # 接受对话框
            self.accept()
            
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {e}")
    
    def get_config(self) -> ConnectionConfig:
        """获取连接配置"""
        return ConnectionConfig(
            host=self.host_edit.text().strip(),
            port=int(self.port_edit.text().strip())
        )