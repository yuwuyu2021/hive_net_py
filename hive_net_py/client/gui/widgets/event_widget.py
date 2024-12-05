"""
事件监控界面模块
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QLabel,
    QSpinBox
)
from PyQt6.QtCore import Qt
from datetime import datetime

class EventWidget(QWidget):
    """事件监控界面类"""
    
    def __init__(self, parent=None):
        """初始化事件监控界面"""
        super().__init__(parent)
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 事件过滤器
        filter_layout = QHBoxLayout()
        
        # 事件类型过滤
        type_label = QLabel("事件类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "全部",
            "连接事件",
            "消息事件",
            "状态变更",
            "错误事件"
        ])
        filter_layout.addWidget(type_label)
        filter_layout.addWidget(self.type_combo)
        
        # 事件数量限制
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
        
        # 事件树形视图
        self.event_tree = QTreeWidget()
        self.event_tree.setHeaderLabels([
            "时间",
            "类型",
            "名称",
            "来源",
            "详情"
        ])
        self.event_tree.setAlternatingRowColors(True)
        layout.addWidget(self.event_tree)
        
        # 连接信号
        self.type_combo.currentTextChanged.connect(self._filter_events)
        self.limit_spin.valueChanged.connect(self._filter_events)
        self.clear_button.clicked.connect(self.clear_events)
    
    def add_event(self, event_type: str, name: str, source: str, details: str):
        """添加事件
        
        Args:
            event_type: 事件类型
            name: 事件名称
            source: 事件来源
            details: 事件详情
        """
        # 创建事件项
        item = QTreeWidgetItem([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event_type,
            name,
            source,
            details
        ])
        
        # 根据事件类型设置颜色
        if "error" in event_type.lower():
            item.setForeground(0, Qt.GlobalColor.red)
        elif "warning" in event_type.lower():
            item.setForeground(0, Qt.GlobalColor.darkYellow)
        
        # 添加到树形视图
        self.event_tree.insertTopLevelItem(0, item)
        
        # 限制显示数量
        while self.event_tree.topLevelItemCount() > self.limit_spin.value():
            self.event_tree.takeTopLevelItem(self.event_tree.topLevelItemCount() - 1)
    
    def _filter_events(self):
        """过滤事件"""
        filter_type = self.type_combo.currentText()
        if filter_type == "全部":
            for i in range(self.event_tree.topLevelItemCount()):
                self.event_tree.topLevelItem(i).setHidden(False)
        else:
            for i in range(self.event_tree.topLevelItemCount()):
                item = self.event_tree.topLevelItem(i)
                item.setHidden(item.text(1) != filter_type)
    
    def clear_events(self):
        """清空事件"""
        self.event_tree.clear() 