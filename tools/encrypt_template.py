#!/usr/bin/env python3
"""
配置模板加密工具
"""
import argparse
import getpass
from pathlib import Path
import sys

from hive_net_py.common.config import (
    JSONConfigLoader,
    YAMLConfigLoader,
    EncryptedTemplateManager,
    TemplateError
)


def get_loader(file_path: Path):
    """根据文件类型获取加载器"""
    suffix = file_path.suffix.lower()
    if suffix == '.json':
        return JSONConfigLoader()
    elif suffix in ('.yml', '.yaml'):
        return YAMLConfigLoader()
    else:
        raise TemplateError(f"Unsupported file type: {suffix}")


def encrypt_template(
    template_dir: Path,
    template_name: str,
    password: str,
    force: bool = False
) -> None:
    """
    加密配置模板
    
    Args:
        template_dir: 模板目录
        template_name: 模板名称
        password: 加密密码
        force: 是否强制加密
    """
    try:
        # 创建模板管理器
        manager = EncryptedTemplateManager(template_dir, password)
        
        # 检查模板是否已加密
        if not force and manager.is_encrypted(template_name):
            print(f"模板已加密: {template_name}", file=sys.stderr)
            sys.exit(1)
        
        # 加载并加密模板
        template_path = template_dir / template_name
        loader = get_loader(template_path)
        
        if manager.is_encrypted(template_name):
            # 先解密再重新加密
            manager.decrypt_template(template_name)
        
        manager.encrypt_existing_template(template_name)
        print(f"模板已加密: {template_name}")
    except Exception as e:
        print(f"加密失败: {e}", file=sys.stderr)
        sys.exit(1)


def decrypt_template(
    template_dir: Path,
    template_name: str,
    password: str
) -> None:
    """
    解密配置模板
    
    Args:
        template_dir: 模板目录
        template_name: 模板名称
        password: 解密密码
    """
    try:
        # 创建模板管理器
        manager = EncryptedTemplateManager(template_dir, password)
        
        # 检查模板是否加密
        if not manager.is_encrypted(template_name):
            print(f"模板未加密: {template_name}", file=sys.stderr)
            sys.exit(1)
        
        # 解密模板
        manager.decrypt_template(template_name)
        print(f"模板已解密: {template_name}")
    except Exception as e:
        print(f"解密失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置模板加密工具")
    parser.add_argument("template", help="模板文件名")
    parser.add_argument("-d", "--template-dir", help="模板目录(默认为templates)")
    parser.add_argument("-p", "--password", help="加密密码(不指定则提示输入)")
    parser.add_argument("--decrypt", action="store_true", help="解密模板")
    parser.add_argument("-f", "--force", action="store_true", help="强制加密(即使已加密)")
    
    args = parser.parse_args()
    
    # 确定模板目录
    template_dir = Path(args.template_dir) if args.template_dir else Path("templates")
    if not template_dir.exists():
        print(f"模板目录不存在: {template_dir}", file=sys.stderr)
        sys.exit(1)
    
    # 检查模板文件
    template_path = template_dir / args.template
    if not template_path.exists():
        print(f"模板文件不存在: {template_path}", file=sys.stderr)
        sys.exit(1)
    
    # 获取密码
    password = args.password
    if not password:
        if args.decrypt:
            password = getpass.getpass("请输入解密密码: ")
        else:
            password = getpass.getpass("请输入加密密码: ")
            confirm = getpass.getpass("请再次输入密码: ")
            if password != confirm:
                print("两次输入的密码不匹配", file=sys.stderr)
                sys.exit(1)
    
    try:
        if args.decrypt:
            decrypt_template(template_dir, args.template, password)
        else:
            encrypt_template(template_dir, args.template, password, args.force)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main() 