"""
消息管理界面模块
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QComboBox,
    QLabel,
    QSpinBox
)
from PyQt6.QtCore import Qt

from ...core.client import MessageType

class MessageWidget(QWidget):
    """消息管理界面类"""
    
    def __init__(self, parent=None):
        """初始化消息管理界面"""
        super().__init__(parent)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 消息过滤器
        filter_layout = QHBoxLayout()
        
        # 消息类型过滤
        type_label = QLabel("消息类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部")
        for msg_type in MessageType:
            self.type_combo.addItem(msg_type.name)
        filter_layout.addWidget(type_label)
        filter_layout.addWidget(self.type_combo)
        
        # 消息数量限制
        limit_label = QLabel("显示数量:")
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 1000)
        self.limit_spin.setValue(100)
        self.limit_spin.setSingleStep(10)
        filter_layout.addWidget(limit_label)
        filter_layout.addWidget(self.limit_spin)
        
        # 清空按钮
        self.clear_button = QPushButton("清空")
        filter_layout.addWidget(self.clear_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 消息显示区域
        self.message_text = QTextEdit()
        self.message_text.setReadOnly(True)
        layout.addWidget(self.message_text)
        
        # 连接信号
        self.type_combo.currentTextChanged.connect(self._filter_messages)
        self.limit_spin.valueChanged.connect(self._filter_messages)
        self.clear_button.clicked.connect(self.clear_messages)
    
    def add_message(self, message: str, msg_type: MessageType = MessageType.NORMAL):
        """添加消息
        
        Args:
            message: 消息内容
            msg_type: 消息类型
        """
        # 根据消息类型设置颜色
        color_map = {
            MessageType.NORMAL: "black",
            MessageType.SYSTEM: "blue",
            MessageType.ERROR: "red",
            MessageType.WARNING: "orange",
            MessageType.INFO: "green",
            MessageType.DEBUG: "gray"
        }
        color = color_map.get(msg_type, "black")
        
        # 添加带颜色的消息
        self.message_text.append(
            f'<span style="color: {color};">[{msg_type.name}] {message}</span>'
        )
    
    def _filter_messages(self):
        """过滤消息"""
        # TODO: 实现消息过滤功能
        pass
    
    def clear_messages(self):
        """清空消息"""
        self.message_text.clear() 