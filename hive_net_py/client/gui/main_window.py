"""
HiveNet 主窗口
"""
import sys
import asyncio
import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QMenuBar,
    QStatusBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction

from .widgets.connection_widget import ConnectionWidget
from .widgets.message_widget import MessageWidget
from .widgets.event_widget import EventWidget
from .dialogs.login_dialog import LoginDialog
from .dialogs.settings_dialog import SettingsDialog
from ..core.client import HiveClient, ClientState, ConnectionConfig

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 信号定义
    connection_status_changed = pyqtSignal(ClientState)
    message_received = pyqtSignal(str)
    event_occurred = pyqtSignal(str)
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 初始化事件循环
        self.loop = asyncio.get_event_loop()
        
        # 客户端实例
        self.client: Optional[HiveClient] = None
        
        # 设置窗口属性
        self.setWindowTitle("HiveNet Client")
        self.setMinimumSize(QSize(800, 600))
        
        # 初始化UI组件
        self._init_ui()
        self._init_menubar()
        self._init_statusbar()
        self._init_signals()
        
        # 显示登录对话框
        self._show_login_dialog()
        
        # 创建定时器以处理异步事件
        self.async_timer = QTimer()
        self.async_timer.timeout.connect(self._process_async_events)
        self.async_timer.start(10)  # 每10毫秒处理一次
    
    def _init_ui(self):
        """初始化UI布局"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 添加功能标签页
        self.connection_widget = ConnectionWidget()
        self.message_widget = MessageWidget()
        self.event_widget = EventWidget()
        
        tab_widget.addTab(self.connection_widget, "连接管理")
        tab_widget.addTab(self.message_widget, "消息")
        tab_widget.addTab(self.event_widget, "事件监控")
    
    def _init_menubar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self._show_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)
    
    def _init_statusbar(self):
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("未连接")
    
    def _init_signals(self):
        """初始化信号连接"""
        # 连接状态变化
        self.connection_status_changed.connect(self._handle_connection_status)
        
        # 消息接收
        self.message_received.connect(self.message_widget.add_message)
        
        # 事件通知
        self.event_occurred.connect(self.event_widget.add_event)
    
    def _show_login_dialog(self):
        """显示登录对话框"""
        dialog = LoginDialog(self)
        if dialog.exec():
            # 登录成功,创建客户端实例
            config = dialog.get_config()
            self.client = HiveClient(config)
            
            # 启动客户端
            self._run_async(self.client.start())
            
            # 连接信号
            self.connection_widget.connect_requested.connect(
                lambda: self._run_async(self.client.connect())
            )
            self.connection_widget.disconnect_requested.connect(
                lambda: self._run_async(self.client.disconnect())
            )
            
            # 更新连接信息
            self.connection_widget.update_connection_info(
                config.host,
                config.port
            )
    
    def _show_settings_dialog(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def _show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 HiveNet",
            "HiveNet 客户端\n\n"
            "版本: 0.1.0\n"
            "一个基于Python的分布式网络系统"
        )
    
    def _handle_connection_status(self, state: ClientState):
        """处理连接状态变化"""
        status_messages = {
            ClientState.DISCONNECTED: "未连接",
            ClientState.CONNECTING: "正在连接...",
            ClientState.CONNECTED: "已连接",
            ClientState.AUTHENTICATING: "正在认证...",
            ClientState.AUTHENTICATED: "已认证",
            ClientState.ERROR: "连接错误"
        }
        self.statusbar.showMessage(status_messages.get(state, "未知状态"))
        
        # 更新连接管理界面
        self.connection_widget.update_status(state)
    
    def _process_async_events(self):
        """处理异步事件"""
        try:
            self.loop.stop()
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"处理异步事件失败: {e}")
    
    def _run_async(self, coro):
        """运行异步协程"""
        try:
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        except Exception as e:
            logger.error(f"运行异步协程失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.client:
            try:
                self.loop.run_until_complete(self.client.stop())
                self.loop.run_until_complete(self.client.disconnect())
            except Exception as e:
                logger.error(f"关闭客户端失败: {e}")
        
        self.async_timer.stop()
        self.loop.stop()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 