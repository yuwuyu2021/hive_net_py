"""
配置热重载模块
"""
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional, Set, Callable, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .loader import ConfigLoader
from .validator import ConfigValidator
from .encryption import ConfigEncryption

logger = logging.getLogger(__name__)

class ConfigReloadHandler(FileSystemEventHandler):
    """配置文件变更处理器"""
    
    def __init__(self, callback: Callable[[str], None]):
        """
        初始化处理器
        
        Args:
            callback: 文件变更回调函数
        """
        self.callback = callback
        self._last_reload_time: Dict[str, float] = {}
        self._cooldown = 1.0  # 冷却时间（秒）
    
    def on_modified(self, event):
        """
        文件修改事件处理
        
        Args:
            event: 文件系统事件
        """
        if not isinstance(event, FileModifiedEvent):
            return
            
        file_path = event.src_path
        current_time = time.time()
        
        # 检查冷却时间
        if file_path in self._last_reload_time:
            if current_time - self._last_reload_time[file_path] < self._cooldown:
                return
        
        self._last_reload_time[file_path] = current_time
        self.callback(file_path)

class ConfigHotReload:
    """配置热重载"""
    
    def __init__(self, 
                 config_dir: str,
                 loader: ConfigLoader,
                 validator: Optional[ConfigValidator] = None,
                 encryption: Optional[ConfigEncryption] = None):
        """
        初始化热重载器
        
        Args:
            config_dir: 配置文件目录
            loader: 配置加载器
            validator: 配置验证器
            encryption: 配置加密器
        """
        self.config_dir = Path(config_dir)
        self.loader = loader
        self.validator = validator
        self.encryption = encryption
        
        self._observer: Optional[Observer] = None
        self._watch_paths: Set[Path] = set()
        self._handlers: Dict[str, Callable] = {}
        self._running = False
    
    def add_watch(self, path: str, handler: Callable[[Dict[str, Any]], None]):
        """
        添加监视路径
        
        Args:
            path: 配置文件路径（相对于config_dir）
            handler: 配置变更处理函数
        """
        abs_path = self.config_dir / path
        if not abs_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {abs_path}")
        
        self._watch_paths.add(abs_path)
        self._handlers[str(abs_path)] = handler
        logger.info(f"添加配置监视: {abs_path}")
    
    def remove_watch(self, path: str):
        """
        移除监视路径
        
        Args:
            path: 配置文件路径（相对于config_dir）
        """
        abs_path = self.config_dir / path
        if str(abs_path) in self._handlers:
            self._watch_paths.remove(abs_path)
            del self._handlers[str(abs_path)]
            logger.info(f"移除配置监视: {abs_path}")
    
    async def start(self):
        """启动热重载器"""
        if self._running:
            return
        
        self._running = True
        self._observer = Observer()
        
        # 创建事件处理器
        handler = ConfigReloadHandler(self._handle_config_change)
        
        # 添加监视
        self._observer.schedule(handler, str(self.config_dir), recursive=True)
        self._observer.start()
        
        logger.info(f"配置热重载��启动，监视目录: {self.config_dir}")
    
    async def stop(self):
        """停止热重载器"""
        if not self._running:
            return
        
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        
        logger.info("配置热重载已停止")
    
    def _handle_config_change(self, file_path: str):
        """
        处理配置文件变更
        
        Args:
            file_path: 变更的文件路径
        """
        try:
            if file_path not in self._handlers:
                return
            
            # 加载新配置
            config = self.loader.load(file_path)
            
            # 解密配置（如果需要）
            if self.encryption:
                config = self.encryption.decrypt(config)
            
            # 验证配置（如果需要）
            if self.validator:
                self.validator.validate(config)
            
            # 调用处理函数
            handler = self._handlers[file_path]
            handler(config)
            
            logger.info(f"配置已重新加载: {file_path}")
            
        except Exception as e:
            logger.error(f"配置重载失败: {e}")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running 