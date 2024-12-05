#!/usr/bin/env python3
"""
配置迁移工具
"""
import argparse
from pathlib import Path
import sys
from typing import Optional

from hive_net_py.common.config import (
    Version,
    VersionManager,
    ConfigError,
    JSONConfigLoader,
    YAMLConfigLoader,
    NetworkConfigMigration_1_0_0_to_1_1_0,
    SecurityConfigMigration_1_1_0_to_1_2_0,
    LoggingConfigMigration_1_2_0_to_1_3_0
)


def get_loader(file_path: Path):
    """根据文件类型获取加载器"""
    suffix = file_path.suffix.lower()
    if suffix == '.json':
        return JSONConfigLoader()
    elif suffix in ('.yml', '.yaml'):
        return YAMLConfigLoader()
    else:
        raise ConfigError(f"Unsupported file type: {suffix}")


def setup_version_manager(config_path: Path, backup_dir: Optional[Path] = None) -> VersionManager:
    """设置版本管理器"""
    loader = get_loader(config_path)
    manager = VersionManager(config_path, loader, backup_dir)
    
    # 添加所有迁移规则
    manager.add_migration(NetworkConfigMigration_1_0_0_to_1_1_0())
    manager.add_migration(SecurityConfigMigration_1_1_0_to_1_2_0())
    manager.add_migration(LoggingConfigMigration_1_2_0_to_1_3_0())
    
    return manager


def print_version_info(manager: VersionManager):
    """打印版本信息"""
    current = manager.get_current_version()
    print(f"当前版本: {current or '未版本化'}")
    
    print("\n可用迁移路径:")
    for from_version, to_version in manager.get_available_migrations():
        print(f"  {from_version} -> {to_version}")
    
    print("\n版本历史:")
    for info in manager.get_history():
        print(f"  {info.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
              f"版本 {info.version}: {info.description}")
        if info.backup_path:
            print(f"    备份: {info.backup_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置迁移工具")
    parser.add_argument("config", help="配置文件路径")
    parser.add_argument("-b", "--backup-dir", help="备份目录路径")
    parser.add_argument("-i", "--info", action="store_true", help="显示版本信息")
    parser.add_argument("-u", "--upgrade", help="升级到指定版本")
    parser.add_argument("-d", "--downgrade", help="降级到指定版本")
    parser.add_argument("-r", "--restore", help="从指定版本的备份恢复")
    parser.add_argument("--no-backup", action="store_true", help="不创建备份")
    parser.add_argument("-m", "--message", help="版本变更说明")
    
    args = parser.parse_args()
    
    try:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"配置文件不存在: {config_path}", file=sys.stderr)
            sys.exit(1)
        
        backup_dir = Path(args.backup_dir) if args.backup_dir else None
        manager = setup_version_manager(config_path, backup_dir)
        
        if args.info:
            print_version_info(manager)
            return
        
        if args.restore:
            try:
                version = Version.from_str(args.restore)
                manager.restore(version)
                print(f"已恢复到版本 {version}")
            except Exception as e:
                print(f"恢复失败: {e}", file=sys.stderr)
                sys.exit(1)
            return
        
        if args.upgrade:
            try:
                version = Version.from_str(args.upgrade)
                manager.upgrade(
                    version,
                    args.message or f"Upgrade to {version}",
                    not args.no_backup
                )
                print(f"已升级到版本 {version}")
            except Exception as e:
                print(f"升级失败: {e}", file=sys.stderr)
                sys.exit(1)
            return
        
        if args.downgrade:
            try:
                version = Version.from_str(args.downgrade)
                manager.downgrade(
                    version,
                    args.message or f"Downgrade to {version}",
                    not args.no_backup
                )
                print(f"已降级到版本 {version}")
            except Exception as e:
                print(f"降级失败: {e}", file=sys.stderr)
                sys.exit(1)
            return
        
        # 如果没有指定操作,显示版本信息
        print_version_info(manager)
        
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main() 