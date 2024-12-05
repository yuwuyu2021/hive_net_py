"""
配置版本控制测试
"""
import pytest
from datetime import datetime
from pathlib import Path
import json
import shutil
from typing import Dict, Any

from hive_net_py.common.config.versioning import (
    Version,
    VersionInfo,
    ConfigMigration,
    VersionManager,
    ConfigError
)
from hive_net_py.common.config.base import JSONConfigLoader
from hive_net_py.common.config.migrations import (
    NetworkConfigMigration_1_0_0_to_1_1_0,
    SecurityConfigMigration_1_1_0_to_1_2_0,
    LoggingConfigMigration_1_2_0_to_1_3_0
)


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """测试配置数据"""
    return {
        'network': {
            'host': '127.0.0.1',
            'port': 8080,
            'timeout': 30
        },
        'security': {
            'auth_required': True,
            'token_expire': 3600
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'logs/hive.log',
            'max_size': 10485760,
            'backup_count': 5
        }
    }


@pytest.fixture
def version_manager(tmp_path, test_config):
    """创建版本管理器实例"""
    config_path = tmp_path / 'config.json'
    backup_dir = tmp_path / 'backups'
    
    # 保存初始配置
    loader = JSONConfigLoader()
    loader.save(test_config, config_path)
    
    # 创建版本管理器
    manager = VersionManager(config_path, loader, backup_dir)
    
    # 添加迁移规则
    manager.add_migration(NetworkConfigMigration_1_0_0_to_1_1_0())
    manager.add_migration(SecurityConfigMigration_1_1_0_to_1_2_0())
    manager.add_migration(LoggingConfigMigration_1_2_0_to_1_3_0())
    
    return manager


def test_version_comparison():
    """测试版本比较"""
    v1 = Version(1, 0, 0)
    v2 = Version(1, 1, 0)
    v3 = Version(1, 1, 1)
    
    assert v1 < v2
    assert v2 < v3
    assert not v2 < v1
    assert str(v1) == "1.0.0"
    
    # 测试版本字符串解析
    v4 = Version.from_str("2.0.1")
    assert v4.major == 2
    assert v4.minor == 0
    assert v4.patch == 1
    
    # 测试无效版本字符串
    with pytest.raises(ConfigError):
        Version.from_str("invalid")


def test_network_config_migration(test_config):
    """测试网络配置迁移"""
    migration = NetworkConfigMigration_1_0_0_to_1_1_0()
    
    # 测试升级
    upgraded = migration.upgrade(test_config.copy())
    assert 'max_retries' in upgraded['network']
    assert 'connection_pool' in upgraded['network']
    assert 'connection_timeout' in upgraded['network']
    assert 'timeout' not in upgraded['network']
    
    # 测试降级
    downgraded = migration.downgrade(upgraded)
    assert 'max_retries' not in downgraded['network']
    assert 'connection_pool' not in downgraded['network']
    assert 'timeout' in downgraded['network']
    assert 'connection_timeout' not in downgraded['network']


def test_security_config_migration(test_config):
    """测试安全配置迁移"""
    migration = SecurityConfigMigration_1_1_0_to_1_2_0()
    
    # 测试升级
    upgraded = migration.upgrade(test_config.copy())
    assert 'authentication' in upgraded['security']
    assert 'encryption' in upgraded['security']
    assert 'rate_limit' in upgraded['security']
    assert 'auth_required' not in upgraded['security']
    
    # 测试降级
    downgraded = migration.downgrade(upgraded)
    assert 'auth_required' in downgraded['security']
    assert 'encryption' not in downgraded['security']
    assert 'rate_limit' not in downgraded['security']


def test_logging_config_migration(test_config):
    """测试日志配置迁移"""
    migration = LoggingConfigMigration_1_2_0_to_1_3_0()
    
    # ���试升级
    upgraded = migration.upgrade(test_config.copy())
    assert 'default' in upgraded['logging']
    assert 'handlers' in upgraded['logging']
    assert 'loggers' in upgraded['logging']
    
    # 测试降级
    downgraded = migration.downgrade(upgraded)
    assert 'level' in downgraded['logging']
    assert 'format' in downgraded['logging']
    assert 'file' in downgraded['logging']
    assert 'handlers' not in downgraded['logging']


def test_version_manager_upgrade(version_manager, test_config):
    """测试版本管理器升级功能"""
    # 升级到1.1.0
    version_manager.upgrade(
        Version(1, 1, 0),
        "Upgrade network config"
    )
    
    config = version_manager.loader.load(version_manager.config_path)
    assert 'max_retries' in config['network']
    assert len(version_manager.get_history()) == 1
    
    # 升级到1.2.0
    version_manager.upgrade(
        Version(1, 2, 0),
        "Upgrade security config"
    )
    
    config = version_manager.loader.load(version_manager.config_path)
    assert 'authentication' in config['security']
    assert len(version_manager.get_history()) == 2
    
    # 尝试降级版本
    with pytest.raises(ConfigError):
        version_manager.upgrade(
            Version(1, 1, 0),
            "Invalid downgrade"
        )


def test_version_manager_downgrade(version_manager, test_config):
    """测试版本管理器降级功能"""
    # 先升级到最新版本
    version_manager.upgrade(
        Version(1, 3, 0),
        "Upgrade to latest"
    )
    
    # 降级到1.2.0
    version_manager.downgrade(
        Version(1, 2, 0),
        "Downgrade logging config"
    )
    
    config = version_manager.loader.load(version_manager.config_path)
    assert 'level' in config['logging']
    assert 'handlers' not in config['logging']
    
    # 降级到1.1.0
    version_manager.downgrade(
        Version(1, 1, 0),
        "Downgrade security config"
    )
    
    config = version_manager.loader.load(version_manager.config_path)
    assert 'auth_required' in config['security']
    assert 'authentication' not in config['security']


def test_version_manager_backup_restore(version_manager, test_config):
    """测试版本管理器备份和恢复功能"""
    # 升级并创建备份
    version_manager.upgrade(
        Version(1, 1, 0),
        "Upgrade with backup",
        auto_backup=True
    )
    
    # 验证备份文件存在
    assert len(list(version_manager.backup_dir.glob('*.bak'))) == 1
    
    # 修改当前配置
    config = version_manager.loader.load(version_manager.config_path)
    config['network']['host'] = '0.0.0.0'
    version_manager.loader.save(config, version_manager.config_path)
    
    # 从备份恢复
    version_manager.restore(Version(1, 1, 0))
    
    # 验证配置已恢复
    restored_config = version_manager.loader.load(version_manager.config_path)
    assert restored_config['network']['host'] == '127.0.0.1'


def test_version_manager_history(version_manager):
    """测试版本管理器历史记录"""
    # 执行多个版本变更
    version_manager.upgrade(Version(1, 1, 0), "Upgrade to 1.1.0")
    version_manager.upgrade(Version(1, 2, 0), "Upgrade to 1.2.0")
    version_manager.downgrade(Version(1, 1, 0), "Downgrade to 1.1.0")
    
    # 验证历史记录
    history = version_manager.get_history()
    assert len(history) == 3
    assert history[0].version == Version(1, 1, 0)
    assert history[1].version == Version(1, 2, 0)
    assert history[2].version == Version(1, 1, 0)
    
    # 验证历史文件
    history_path = version_manager.config_path.with_suffix('.history')
    assert history_path.exists()
    
    with open(history_path, 'r', encoding='utf-8') as f:
        history_data = json.load(f)
    assert len(history_data) == 3 