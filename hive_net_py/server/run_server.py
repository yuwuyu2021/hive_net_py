"""
HiveNet 服务器启动脚本
"""
import sys
import argparse
import logging
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from .core.server import HiveServer
from .gui.main_window import MainWindow

def setup_logging(log_level: str = "INFO"):
    """设置日志"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 设置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            log_dir / "server.log",
            encoding='utf-8',
            mode='a'
        )
    ]
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )

async def run_server_cli(host: str, port: int):
    """以命令行模式运行服务器"""
    server = HiveServer(host, port)
    try:
        await server.start()
        logging.info(f"服务器已启动于 {host}:{port}")
        
        # 等待中断���号
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("正在停止服务器...")
    except Exception as e:
        logging.error(f"服务器运行出错: {e}")
    finally:
        await server.stop()
        logging.info("服务器已停止")

def run_server_gui():
    """以GUI模式运行服务器"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("HiveNet Server")
    app.setApplicationVersion("0.1.0")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    return app.exec()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="HiveNet 服务器")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="服务器端口 (默认: 8888)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="以命令行模式运行（不启动GUI）"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    try:
        if args.no_gui:
            # 命令行模式
            asyncio.run(run_server_cli(args.host, args.port))
        else:
            # GUI模式
            sys.exit(run_server_gui())
    except Exception as e:
        logging.error(f"启动服务器失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 