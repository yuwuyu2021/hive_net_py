"""
日志查看器组件
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QComboBox,
    QLabel,
    QSpinBox,
    QCheckBox,
    QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from datetime import datetime

class LogViewer(QWidget):
    """日志查看器组件类"""
    
    # 日志级别颜色映射
    LEVEL_COLORS = {
        "DEBUG": QColor(128, 128, 128),  # 灰色
        "INFO": QColor(0, 0, 0),         # 黑色
        "WARNING": QColor(255, 165, 0),   # 橙色
        "ERROR": QColor(255, 0, 0),       # 红色
        "CRITICAL": QColor(139, 0, 0)     # 深红色
    }
    
    def __init__(self, parent=None):
        """初始化日志查看器"""
        super().__init__(parent)
        
        # 初始化数据
        self.max_lines = 1000
        self.auto_scroll = True
        self.show_timestamp = True
        self.current_filter = "ALL"
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar_group = QGroupBox("日志控制")
        toolbar_layout = QHBoxLayout(toolbar_group)
        
        # 日志级别过滤
        level_label = QLabel("日志级别:")
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "ALL",
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL"
        ])
        toolbar_layout.addWidget(level_label)
        toolbar_layout.addWidget(self.level_combo)
        
        # 最大行数
        lines_label = QLabel("最大行数:")
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(100, 10000)
        self.lines_spin.setValue(self.max_lines)
        self.lines_spin.setSingleStep(100)
        toolbar_layout.addWidget(lines_label)
        toolbar_layout.addWidget(self.lines_spin)
        
        # 自动滚动
        self.scroll_check = QCheckBox("自动滚动")
        self.scroll_check.setChecked(self.auto_scroll)
        toolbar_layout.addWidget(self.scroll_check)
        
        # 显示时间戳
        self.timestamp_check = QCheckBox("显示时间戳")
        self.timestamp_check.setChecked(self.show_timestamp)
        toolbar_layout.addWidget(self.timestamp_check)
        
        # 清空按钮
        self.clear_button = QPushButton("清空")
        toolbar_layout.addWidget(self.clear_button)
        
        # 导出按钮
        self.export_button = QPushButton("导出")
        toolbar_layout.addWidget(self.export_button)
        
        toolbar_layout.addStretch()
        layout.addWidget(toolbar_group)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_text)
        
        # 连接信号
        self.level_combo.currentTextChanged.connect(self._handle_filter_changed)
        self.lines_spin.valueChanged.connect(self._handle_max_lines_changed)
        self.scroll_check.stateChanged.connect(self._handle_auto_scroll_changed)
        self.timestamp_check.stateChanged.connect(self._handle_timestamp_changed)
        self.clear_button.clicked.connect(self.clear_logs)
        self.export_button.clicked.connect(self._handle_export)
    
    def add_log(self, message: str, level: str = "INFO"):
        """添加日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        # 检查日志级别过滤
        if self.current_filter != "ALL" and level != self.current_filter:
            return
        
        # 创建日志文本
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.show_timestamp:
            log_text = f"[{timestamp}] [{level}] {message}"
        else:
            log_text = f"[{level}] {message}"
        
        # 设置文本格式
        format = QTextCharFormat()
        format.setForeground(self.LEVEL_COLORS.get(level, QColor(0, 0, 0)))
        
        # 添加日志
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(log_text + "\n", format)
        
        # 检查最大行数
        document = self.log_text.document()
        if document.lineCount() > self.max_lines:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                document.lineCount() - self.max_lines
            )
            cursor.removeSelectedText()
        
        # 自动滚动
        if self.auto_scroll:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.clear()
    
    def _handle_filter_changed(self, level: str):
        """处理过滤器变化
        
        Args:
            level: 新的日志级别
        """
        self.current_filter = level
    
    def _handle_max_lines_changed(self, value: int):
        """处理最大行数变化
        
        Args:
            value: 新的最大行数
        """
        self.max_lines = value
        
        # 检查并裁剪现有日志
        document = self.log_text.document()
        if document.lineCount() > self.max_lines:
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                document.lineCount() - self.max_lines
            )
            cursor.removeSelectedText()
    
    def _handle_auto_scroll_changed(self, state: int):
        """处理自动滚动变化
        
        Args:
            state: 新的状态
        """
        self.auto_scroll = state == Qt.CheckState.Checked.value
    
    def _handle_timestamp_changed(self, state: int):
        """处理时间戳显示变化
        
        Args:
            state: 新的状态
        """
        self.show_timestamp = state == Qt.CheckState.Checked.value
    
    def _handle_export(self):
        """处理导出按钮点击"""
        # TODO: 实现日志导出功能
        pass