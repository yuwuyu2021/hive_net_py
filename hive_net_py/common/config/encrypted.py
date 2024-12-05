"""
加密配置加载器模块
"""
import base64
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .base import ConfigLoader, ConfigError, JSONConfigLoader, YAMLConfigLoader


def generate_key(password: str, salt: Optional[bytes] = None) -> bytes:
    """从密码生成加密密钥"""
    if salt is None:
        salt = b'hive_net_salt'  # 默认盐值
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


class EncryptedConfigLoader(ConfigLoader):
    """加密配置加载器"""
    
    def __init__(self, base_loader: ConfigLoader, password: str):
        """
        初始化加密配置加载器
        
        Args:
            base_loader: 基础配置加载器(JSON或YAML)
            password: 加密密码
        """
        self.base_loader = base_loader
        self.fernet = Fernet(generate_key(password))
    
    def load(self, path: Path) -> Dict[str, Any]:
        """加载并解密配置"""
        try:
            with open(path, 'rb') as f:
                encrypted_data = f.read()
            
            # 尝试解密
            try:
                decrypted_data = self.fernet.decrypt(encrypted_data)
                # 创建临时文件用于加载解密后的数据
                temp_path = path.with_suffix(path.suffix + '.temp')
                with open(temp_path, 'wb') as f:
                    f.write(decrypted_data)
                
                try:
                    # 使用基础加载器加载解密后的数据
                    config = self.base_loader.load(temp_path)
                finally:
                    # 清理临时文件
                    temp_path.unlink()
                
                return config
            except Exception as e:
                raise ConfigError(f"Failed to decrypt config: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load encrypted config: {e}")
    
    def save(self, config: Dict[str, Any], path: Path) -> None:
        """加密并保存配置"""
        try:
            # 创建临时文件用于保存原始数据
            temp_path = path.with_suffix(path.suffix + '.temp')
            try:
                # 使用基础加载器保存原始数据
                self.base_loader.save(config, temp_path)
                
                # 读取原始数据并加密
                with open(temp_path, 'rb') as f:
                    data = f.read()
                encrypted_data = self.fernet.encrypt(data)
                
                # 保存加密数据
                with open(path, 'wb') as f:
                    f.write(encrypted_data)
            finally:
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
        except Exception as e:
            raise ConfigError(f"Failed to save encrypted config: {e}")


def create_encrypted_loader(
    file_type: str,
    password: str
) -> EncryptedConfigLoader:
    """
    创建加密配置加载器
    
    Args:
        file_type: 文件类型 ('json' 或 'yaml')
        password: 加密密码
    
    Returns:
        EncryptedConfigLoader 实例
    """
    if file_type.lower() == 'json':
        base_loader = JSONConfigLoader()
    elif file_type.lower() in ('yaml', 'yml'):
        base_loader = YAMLConfigLoader()
    else:
        raise ConfigError(f"Unsupported file type: {file_type}")
    
    return EncryptedConfigLoader(base_loader, password) 