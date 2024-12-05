#!/usr/bin/env python3
"""
启动服务器脚本
"""
import sys
import logging
import asyncio
import argparse
from pathlib import Path
import qasync
from PyQt6.QtWidgets import QApplication

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from hive_net_py.server.core.server import HiveServer
from hive_net_py.server.core.session import SessionManager
from hive_net_py.server.core.monitor import PerformanceMonitor
from hive_net_py.server.gui.main_window import MainWindow

# 设置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            log_dir / "server.log",
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

async def run_server_cli(host: str, port: int):
    """以命令行模式运行服务器"""
    try:
        # 启动性能监控
        monitor = PerformanceMonitor()
        await monitor.start()
        
        # 创建会话管理器
        session_manager = SessionManager()
        await session_manager.start()
        
        # 创建并启动服务器
        server = HiveServer(host=host, port=port)
        await server.start()
        
        logger.info(f"服务器已启动于 {host}:{port}")
        
        # 等待服务器运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        
        # 停止服务器
        await server.stop()
        await session_manager.stop()
        await monitor.stop()
        
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        sys.exit(1)

def run_server_gui():
    """以GUI模式运行服务器"""
    try:
        app = QApplication(sys.argv)
        
        # 设置应用信息
        app.setApplicationName("HiveNet Server")
        app.setApplicationVersion("0.1.0")
        
        # 创建事件循环
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # 创建主窗口
        window = MainWindow(loop=loop)
        window.show()
        
        # 运行事件循环
        with loop:
            loop.run_forever()
        
    except Exception as e:
        logger.error(f"GUI启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HiveNet 服务器")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="服务器主机地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="服务器端口 (默认: 8080)"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="以命令行模式运行（不启动GUI）"
    )
    
    args = parser.parse_args()
    
    try:
        if args.no_gui:
            # 命令行模式
            asyncio.run(run_server_cli(args.host, args.port))
        else:
            # GUI模式
            run_server_gui()
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 