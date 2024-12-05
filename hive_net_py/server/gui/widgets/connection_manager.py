"""
连接管理器组件
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QGroupBox
)
from PyQt6.QtCore import Qt
from datetime import datetime

class ConnectionManager(QWidget):
    """连接管理器组件类"""
    
    def __init__(self, parent=None):
        """初始化连接管理器"""
        super().__init__(parent)
        
        # 初始化数据
        self.connections = {}  # client_id -> QTreeWidgetItem
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 统计信息
        stats_group = QGroupBox("连接统计")
        stats_layout = QHBoxLayout(stats_group)
        
        # 当前连接数
        current_label = QLabel("当前连接数:")
        self.current_value = QLabel("0")
        stats_layout.addWidget(current_label)
        stats_layout.addWidget(self.current_value)
        
        # 历史连接数
        total_label = QLabel("历史连接数:")
        self.total_value = QLabel("0")
        stats_layout.addWidget(total_label)
        stats_layout.addWidget(self.total_value)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        stats_layout.addWidget(self.refresh_button)
        
        stats_layout.addStretch()
        layout.addWidget(stats_group)
        
        # 连接列表
        self.connection_tree = QTreeWidget()
        self.connection_tree.setHeaderLabels([
            "客户端ID",
            "IP地址",
            "连接时间",
            "状态",
            "消息数",
            "最后活动"
        ])
        self.connection_tree.setAlternatingRowColors(True)
        layout.addWidget(self.connection_tree)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.setEnabled(False)
        button_layout.addWidget(self.disconnect_button)
        
        self.disconnect_all_button = QPushButton("断开所有")
        button_layout.addWidget(self.disconnect_all_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 连接信号
        self.refresh_button.clicked.connect(self.refresh)
        self.disconnect_button.clicked.connect(self._disconnect_selected)
        self.disconnect_all_button.clicked.connect(self._disconnect_all)
        self.connection_tree.itemSelectionChanged.connect(self._update_button_state)
    
    def add_connection(self, client_id: str, ip_address: str):
        """添加连接
        
        Args:
            client_id: 客户端ID
            ip_address: IP地址
        """
        if client_id not in self.connections:
            item = QTreeWidgetItem([
                client_id,
                ip_address,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "已连接",
                "0",
                "刚刚"
            ])
            self.connection_tree.addTopLevelItem(item)
            self.connections[client_id] = item
            self._update_stats()
    
    def remove_connection(self, client_id: str):
        """移除连接
        
        Args:
            client_id: 客户端ID
        """
        if client_id in self.connections:
            item = self.connections[client_id]
            index = self.connection_tree.indexOfTopLevelItem(item)
            self.connection_tree.takeTopLevelItem(index)
            del self.connections[client_id]
            self._update_stats()
    
    def update_connection(self, client_id: str, status: str = None, 
                         message_count: int = None, last_activity: str = None):
        """更新连接信息
        
        Args:
            client_id: 客户端ID
            status: 连接状态
            message_count: 消息数
            last_activity: 最后活动时间
        """
        if client_id in self.connections:
            item = self.connections[client_id]
            if status is not None:
                item.setText(3, status)
            if message_count is not None:
                item.setText(4, str(message_count))
            if last_activity is not None:
                item.setText(5, last_activity)
    
    def update_stats(self, current_count: int, total_count: int):
        """更新统计信息
        
        Args:
            current_count: 当前连接数
            total_count: 历史连接数
        """
        self.current_value.setText(str(current_count))
        self.total_value.setText(str(total_count))
    
    def refresh(self):
        """刷新连接列表"""
        # TODO: 实现刷新逻辑
        pass
    
    def _disconnect_selected(self):
        """断开选中的连接"""
        selected_items = self.connection_tree.selectedItems()
        for item in selected_items:
            client_id = item.text(0)
            # TODO: 实现断开连接逻辑
            self.remove_connection(client_id)
    
    def _disconnect_all(self):
        """断开所有连接"""
        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            # TODO: 实现断开连接逻辑
            self.remove_connection(client_id)
    
    def _update_button_state(self):
        """更新按钮状态"""
        self.disconnect_button.setEnabled(
            len(self.connection_tree.selectedItems()) > 0
        )
        self.disconnect_all_button.setEnabled(
            self.connection_tree.topLevelItemCount() > 0
        )
    
    def _update_stats(self):
        """更新统计信息"""
        current_count = self.connection_tree.topLevelItemCount()
        self.current_value.setText(str(current_count)) 