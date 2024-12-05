"""
服务器主窗口
"""
import sys
import asyncio
import logging
import qasync
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QLineEdit,
    QStatusBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer

from ..core.server import HiveServer
from ..core.session import SessionManager
from ..core.monitor import PerformanceMonitor
from .widgets.control_panel import ControlPanel
from .widgets.connection_manager import ConnectionManager
from .widgets.log_viewer import LogViewer
from .widgets.performance_monitor import PerformanceMonitor as PerformanceWidget

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """服务器主窗口类"""
    
    def __init__(self, loop=None):
        """初始化主窗口
        
        Args:
            loop: 事件循环
        """
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle("HiveNet Server")
        self.setMinimumSize(800, 600)
        
        # 保存事件循环
        self.loop = loop or asyncio.get_event_loop()
        
        # 创建组件
        self.server = None
        self.session_manager = None
        self.performance_monitor = None
        self.update_timer = None
        
        # 初始化UI
        self._init_ui()
        
        # 启动定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # 每秒更新一次
    
    def _init_ui(self):
        """初始化UI"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建服务器控制面板
        control_group = QWidget()
        control_layout = QHBoxLayout(control_group)
        
        # 主机地址输入
        host_label = QLabel("主机地址:")
        self.host_edit = QLineEdit("0.0.0.0")
        control_layout.addWidget(host_label)
        control_layout.addWidget(self.host_edit)
        
        # 端口输入
        port_label = QLabel("端口:")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8080)
        control_layout.addWidget(port_label)
        control_layout.addWidget(self.port_spin)
        
        # 启动/停止按钮
        self.start_button = QPushButton("启动服务器")
        self.stop_button = QPushButton("停止服务器")
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        control_layout.addStretch()
        layout.addWidget(control_group)
        
        # 创建标签页
        self.control_panel = ControlPanel()
        self.connection_manager = ConnectionManager()
        self.log_viewer = LogViewer()
        self.performance_widget = PerformanceWidget()
        
        # 添加到主布局
        layout.addWidget(self.control_panel)
        layout.addWidget(self.connection_manager)
        layout.addWidget(self.log_viewer)
        layout.addWidget(self.performance_widget)
        
        # 创建状态栏
        self.statusBar().showMessage("服务器未启动")
        
        # 连接信号
        self.start_button.clicked.connect(self._start_server)
        self.stop_button.clicked.connect(self._stop_server)
    
    async def _init_server(self):
        """初始化服务器组件"""
        try:
            # 创建性能监控器
            self.performance_monitor = PerformanceMonitor()
            await self.performance_monitor.start()
            
            # 创建会话管理器
            self.session_manager = SessionManager()
            await self.session_manager.start()
            
            # 创建服务器
            host = self.host_edit.text()
            port = self.port_spin.value()
            self.server = HiveServer(host=host, port=port)
            await self.server.start()
            
            # 更新UI状态
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.host_edit.setEnabled(False)
            self.port_spin.setEnabled(False)
            
            self.statusBar().showMessage(f"服务器运行中 - {host}:{port}")
            self.log_viewer.add_log("服务器已启动", "INFO")
            
        except Exception as e:
            self.log_viewer.add_log(f"服务器启动失败: {e}", "ERROR")
            raise
    
    async def _cleanup_server(self):
        """清理服务器组件"""
        try:
            if self.server:
                await self.server.stop()
                self.server = None
            
            if self.session_manager:
                await self.session_manager.stop()
                self.session_manager = None
            
            if self.performance_monitor:
                await self.performance_monitor.stop()
                self.performance_monitor = None
            
            # 更新UI状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.host_edit.setEnabled(True)
            self.port_spin.setEnabled(True)
            
            self.statusBar().showMessage("服务器已停止")
            self.log_viewer.add_log("服务器已停止", "INFO")
            
        except Exception as e:
            self.log_viewer.add_log(f"服务器停止失败: {e}", "ERROR")
            raise
    
    def _start_server(self):
        """启动服务器"""
        asyncio.run_coroutine_threadsafe(self._init_server(), self.loop)
    
    def _stop_server(self):
        """停止服务器"""
        asyncio.run_coroutine_threadsafe(self._cleanup_server(), self.loop)
    
    def _update_status(self):
        """更新状态"""
        if self.server and self.server.is_running:
            # 更新连接信息
            active_sessions = len(self.session_manager.active_sessions)
            total_sessions = self.session_manager.session_count
            self.connection_manager.update_stats(active_sessions, total_sessions)
            
            # 更新性能信息
            if self.performance_monitor:
                stats = self.performance_monitor.get_stats()
                self.performance_widget.update_stats(stats)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.server and self.server.is_running:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "服务器正在运行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                asyncio.run_coroutine_threadsafe(self._cleanup_server(), self.loop)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() 