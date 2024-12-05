"""
HiveNet 服务器GUI启动脚本
"""
import sys
import logging
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow

def setup_logging():
    """设置日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                log_dir / "server_gui.log",
                encoding='utf-8',
                mode='w'
            )
        ]
    )

def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 创建应用
        app = QApplication(sys.argv)
        
        # 设置应用信息
        app.setApplicationName("HiveNet Server")
        app.setApplicationVersion("0.1.0")
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # ���建主窗口
        window = MainWindow()
        window.show()
        
        # 运行应用
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("应用启动失败")
        sys.exit(1)

if __name__ == '__main__':
    main() 