"""
配置基类模块
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class ConnectionConfig:
    """连接配置类"""
    
    host: str = "localhost"
    port: int = 8080
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 1
    keep_alive: bool = True
    buffer_size: int = 8192
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    auth_enabled: bool = False
    auth_token: Optional[str] = None

@dataclass
class ServerConfig:
    """服务器配置类"""
    
    host: str = "0.0.0.0"
    port: int = 8080
    max_connections: int = 1000
    thread_pool_size: int = 10
    timeout: int = 30
    buffer_size: int = 8192
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    auth_enabled: bool = False
    auth_token: Optional[str] = None

@dataclass
class LogConfig:
    """日志配置类"""
    
    level: str = "INFO"
    file_enabled: bool = True
    file_path: str = "logs/server.log"
    max_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

@dataclass
class MonitorConfig:
    """监控配置类"""
    
    enabled: bool = True
    interval: int = 5
    history_size: int = 3600
    perf_enabled: bool = True
    network_enabled: bool = True
    alert_enabled: bool = True
    alert_threshold_cpu: float = 80.0
    alert_threshold_memory: float = 80.0
    alert_threshold_disk: float = 90.0 