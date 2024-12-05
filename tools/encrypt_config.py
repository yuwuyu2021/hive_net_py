#!/usr/bin/env python3
"""
配置文件加密工具
"""
import argparse
import getpass
from pathlib import Path
import sys

from hive_net_py.common.config.encrypted import create_encrypted_loader
from hive_net_py.common.config.base import ConfigError


def encrypt_config(input_path: Path, output_path: Path, password: str) -> None:
    """
    加密配置文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        password: 加密密码
    """
    # 根据文件扩展名确定类型
    file_type = input_path.suffix.lstrip('.')
    if file_type not in ('json', 'yaml', 'yml'):
        raise ConfigError(f"Unsupported file type: {file_type}")
    
    # 创建加密加载器
    loader = create_encrypted_loader(file_type, password)
    
    try:
        # 加载原始配置
        base_loader = loader.base_loader
        config = base_loader.load(input_path)
        
        # 保存加密配置
        loader.save(config, output_path)
        print(f"配置已加密并保存到: {output_path}")
    except Exception as e:
        print(f"加密失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置文件加密工具")
    parser.add_argument("input", help="输入配置文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径(默认为输入文件名.enc)")
    parser.add_argument("-p", "--password", help="加密密码(不指定则提示输入)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(input_path.suffix + '.enc')
    
    # 获取密码
    password = args.password
    if not password:
        password = getpass.getpass("请输入加密密码: ")
        confirm = getpass.getpass("请再次输入密码: ")
        if password != confirm:
            print("两次输入的密码不匹配", file=sys.stderr)
            sys.exit(1)
    
    try:
        encrypt_config(input_path, output_path, password)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main() 