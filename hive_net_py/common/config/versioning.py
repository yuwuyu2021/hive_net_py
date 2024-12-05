"""
配置版本控制模块
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import shutil

from .base import ConfigError, ConfigLoader


@dataclass
class Version:
    """配置版本信息"""
    major: int  # 主版本号
    minor: int  # 次版本号
    patch: int  # 补丁版本号
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @classmethod
    def from_str(cls, version_str: str) -> 'Version':
        """从字符串创建版本对象"""
        try:
            major, minor, patch = map(int, version_str.split('.'))
            return cls(major, minor, patch)
        except Exception as e:
            raise ConfigError(f"Invalid version string: {version_str}")
    
    def __lt__(self, other: 'Version') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


@dataclass
class VersionInfo:
    """版本详细信息"""
    version: Version
    timestamp: datetime
    description: str
    changes: Dict[str, Any]
    backup_path: Optional[Path] = None


class ConfigMigration:
    """配置迁移基类"""
    
    def __init__(self, from_version: Version, to_version: Version):
        self.from_version = from_version
        self.to_version = to_version
    
    def upgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """升级配置"""
        raise NotImplementedError
    
    def downgrade(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """降级配置"""
        raise NotImplementedError


class VersionManager:
    """配置版本管理器"""
    
    def __init__(
        self,
        config_path: Path,
        loader: ConfigLoader,
        backup_dir: Optional[Path] = None
    ):
        self.config_path = config_path
        self.loader = loader
        self.backup_dir = backup_dir or config_path.parent / 'backups'
        self.migrations: List[ConfigMigration] = []
        self.version_history: List[VersionInfo] = []
        self._load_history()
    
    def _load_history(self) -> None:
        """加载版本历史"""
        history_path = self.config_path.with_suffix('.history')
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                for entry in history_data:
                    version_info = VersionInfo(
                        version=Version.from_str(entry['version']),
                        timestamp=datetime.fromisoformat(entry['timestamp']),
                        description=entry['description'],
                        changes=entry['changes'],
                        backup_path=Path(entry['backup_path']) if entry.get('backup_path') else None
                    )
                    self.version_history.append(version_info)
            except Exception as e:
                raise ConfigError(f"Failed to load version history: {e}")
    
    def _save_history(self) -> None:
        """保存版本历史"""
        history_path = self.config_path.with_suffix('.history')
        try:
            history_data = [
                {
                    'version': str(info.version),
                    'timestamp': info.timestamp.isoformat(),
                    'description': info.description,
                    'changes': info.changes,
                    'backup_path': str(info.backup_path) if info.backup_path else None
                }
                for info in self.version_history
            ]
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"Failed to save version history: {e}")
    
    def _create_backup(self, config: Dict[str, Any], version: Version) -> Path:
        """创建配置备份"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / f"config_v{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        
        try:
            self.loader.save(config, backup_path)
            return backup_path
        except Exception as e:
            raise ConfigError(f"Failed to create backup: {e}")
    
    def add_migration(self, migration: ConfigMigration) -> None:
        """添加迁移规则"""
        self.migrations.append(migration)
        # 按版本号排序
        self.migrations.sort(key=lambda m: (m.from_version, m.to_version))
    
    def get_current_version(self) -> Optional[Version]:
        """获取当前版本"""
        if not self.version_history:
            return None
        return self.version_history[-1].version
    
    def upgrade(
        self,
        target_version: Version,
        description: str,
        auto_backup: bool = True
    ) -> None:
        """升级配置到指定版本"""
        current_version = self.get_current_version()
        if current_version and current_version >= target_version:
            raise ConfigError(f"Current version {current_version} is not lower than target version {target_version}")
        
        # 加载当前配置
        config = self.loader.load(self.config_path)
        original_config = config.copy()
        changes = {}
        
        try:
            # 查找并应用迁移规则
            for migration in self.migrations:
                if (current_version is None or migration.from_version > current_version) and migration.to_version <= target_version:
                    config = migration.upgrade(config)
                    changes[str(migration.from_version)] = {
                        'to_version': str(migration.to_version),
                        'type': 'upgrade'
                    }
            
            # 创建备份
            backup_path = self._create_backup(original_config, target_version) if auto_backup else None
            
            # 保存新配置
            self.loader.save(config, self.config_path)
            
            # 记录版本信息
            version_info = VersionInfo(
                version=target_version,
                timestamp=datetime.now(),
                description=description,
                changes=changes,
                backup_path=backup_path
            )
            self.version_history.append(version_info)
            self._save_history()
            
        except Exception as e:
            # 如果升级失败,尝试恢复原始配置
            try:
                self.loader.save(original_config, self.config_path)
            except Exception:
                pass
            raise ConfigError(f"Failed to upgrade config: {e}")
    
    def downgrade(
        self,
        target_version: Version,
        description: str,
        auto_backup: bool = True
    ) -> None:
        """降级配置到指定版本"""
        current_version = self.get_current_version()
        if current_version is None:
            raise ConfigError("No version history found")
        if current_version <= target_version:
            raise ConfigError(f"Current version {current_version} is not higher than target version {target_version}")
        
        # 加载当前配置
        config = self.loader.load(self.config_path)
        original_config = config.copy()
        changes = {}
        
        try:
            # 查找并应用迁移规则
            for migration in reversed(self.migrations):
                if migration.from_version >= target_version and migration.to_version <= current_version:
                    config = migration.downgrade(config)
                    changes[str(migration.to_version)] = {
                        'to_version': str(migration.from_version),
                        'type': 'downgrade'
                    }
            
            # 创建备份
            backup_path = self._create_backup(original_config, target_version) if auto_backup else None
            
            # 保存新配置
            self.loader.save(config, self.config_path)
            
            # 记录版本信息
            version_info = VersionInfo(
                version=target_version,
                timestamp=datetime.now(),
                description=description,
                changes=changes,
                backup_path=backup_path
            )
            self.version_history.append(version_info)
            self._save_history()
            
        except Exception as e:
            # 如果降级失败,尝试恢复原始配置
            try:
                self.loader.save(original_config, self.config_path)
            except Exception:
                pass
            raise ConfigError(f"Failed to downgrade config: {e}")
    
    def restore(self, version: Version) -> None:
        """从备份恢复配置"""
        # 查找指定版本的备份
        version_info = next(
            (info for info in self.version_history if info.version == version),
            None
        )
        
        if not version_info or not version_info.backup_path:
            raise ConfigError(f"No backup found for version {version}")
        
        try:
            # 复制备份文件
            shutil.copy2(version_info.backup_path, self.config_path)
            
            # 记录恢复操作
            restore_info = VersionInfo(
                version=version,
                timestamp=datetime.now(),
                description=f"Restored from backup {version_info.backup_path}",
                changes={'type': 'restore', 'from_backup': str(version_info.backup_path)},
                backup_path=None
            )
            self.version_history.append(restore_info)
            self._save_history()
            
        except Exception as e:
            raise ConfigError(f"Failed to restore config: {e}")
    
    def get_history(self) -> List[VersionInfo]:
        """获取版本历史"""
        return self.version_history.copy()
    
    def get_available_migrations(
        self,
        from_version: Optional[Version] = None
    ) -> List[Tuple[Version, Version]]:
        """获取可用的迁移路径"""
        if from_version is None:
            from_version = self.get_current_version()
        if from_version is None:
            return [(m.from_version, m.to_version) for m in self.migrations]
        
        return [
            (m.from_version, m.to_version)
            for m in self.migrations
            if m.from_version >= from_version
        ] 