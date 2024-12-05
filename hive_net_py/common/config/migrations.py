"""
配置迁移规则示例
"""
from typing import Any, Dict

from .versioning import ConfigMigration, Version


class NetworkConfigMigration_1_0_0_to_1_1_0(ConfigMigration):
    """网络配置从1.0.0升级到1.1.0的迁移规则"""
    
    def __init__(self):
        super().__init__(
            Version(1, 0, 0),
            Version(1, 1, 0)
        )
    
    def upgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        升级配置:
        1. 添加新的网络配置选项
        2. 重命名部分字段
        """
        if 'network' in config:
            network = config['network']
            
            # 添加新的配置选项
            network.setdefault('max_retries', 3)
            network.setdefault('retry_interval', 5)
            network.setdefault('connection_pool', {
                'max_size': 100,
                'timeout': 30
            })
            
            # 重命名字段
            if 'timeout' in network:
                network['connection_timeout'] = network.pop('timeout')
        
        return config
    
    def downgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        降级配置:
        1. 移除新添加的选项
        2. 恢复字段名
        """
        if 'network' in config:
            network = config['network']
            
            # 移除新添加的选项
            network.pop('max_retries', None)
            network.pop('retry_interval', None)
            network.pop('connection_pool', None)
            
            # 恢复字段名
            if 'connection_timeout' in network:
                network['timeout'] = network.pop('connection_timeout')
        
        return config


class SecurityConfigMigration_1_1_0_to_1_2_0(ConfigMigration):
    """安全配置从1.1.0升级到1.2.0的迁移规则"""
    
    def __init__(self):
        super().__init__(
            Version(1, 1, 0),
            Version(1, 2, 0)
        )
    
    def upgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        升级配置:
        1. 添加新的安全配置选项
        2. 更新认证配置结构
        """
        if 'security' in config:
            security = config['security']
            
            # 更新认证配置结构
            if 'auth_required' in security:
                auth_config = {
                    'enabled': security.pop('auth_required'),
                    'methods': ['password'],
                    'token': {
                        'expire': security.pop('token_expire', 3600),
                        'refresh_enabled': True,
                        'refresh_expire': 86400
                    }
                }
                security['authentication'] = auth_config
            
            # 添加新的安全选项
            security.setdefault('encryption', {
                'enabled': True,
                'algorithm': 'AES-256-GCM',
                'key_rotation': 86400
            })
            
            security.setdefault('rate_limit', {
                'enabled': True,
                'max_requests': 1000,
                'window': 3600
            })
        
        return config
    
    def downgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        降级配置:
        1. 恢复旧的认证配置结构
        2. 移除新添加的安全选项
        """
        if 'security' in config:
            security = config['security']
            
            # 恢复旧的认证配置结构
            if 'authentication' in security:
                auth = security.pop('authentication')
                security['auth_required'] = auth['enabled']
                if 'token' in auth:
                    security['token_expire'] = auth['token']['expire']
            
            # 移除新添加的安全选项
            security.pop('encryption', None)
            security.pop('rate_limit', None)
        
        return config


class LoggingConfigMigration_1_2_0_to_1_3_0(ConfigMigration):
    """日志配置从1.2.0升级到1.3.0的迁移规则"""
    
    def __init__(self):
        super().__init__(
            Version(1, 2, 0),
            Version(1, 3, 0)
        )
    
    def upgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        升级配置:
        1. 重构日志配置结构
        2. 添加新的日志功能
        """
        if 'logging' in config:
            old_logging = config.pop('logging')
            
            # 创建新的日志配置结构
            config['logging'] = {
                'default': {
                    'level': old_logging.get('level', 'INFO'),
                    'format': old_logging.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
                    'handlers': ['file', 'console']
                },
                'handlers': {
                    'console': {
                        'type': 'console',
                        'level': 'INFO'
                    },
                    'file': {
                        'type': 'file',
                        'filename': old_logging.get('file', 'logs/hive.log'),
                        'max_size': old_logging.get('max_size', 10485760),
                        'backup_count': old_logging.get('backup_count', 5),
                        'encoding': 'utf-8'
                    }
                },
                'loggers': {
                    'hive': {
                        'level': 'INFO',
                        'handlers': ['file', 'console'],
                        'propagate': False
                    }
                }
            }
        
        return config
    
    def downgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        降级配置:
        1. 恢复旧的日志配置结构
        """
        if 'logging' in config:
            new_logging = config.pop('logging')
            
            # 恢复旧的日志配置结构
            config['logging'] = {
                'level': new_logging['default']['level'],
                'format': new_logging['default']['format'],
                'file': new_logging['handlers']['file']['filename'],
                'max_size': new_logging['handlers']['file']['max_size'],
                'backup_count': new_logging['handlers']['file']['backup_count']
            }
        
        return config 