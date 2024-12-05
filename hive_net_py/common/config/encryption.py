"""
配置加密模块
"""
import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ConfigEncryption(ABC):
    """配置加密基类"""
    
    @abstractmethod
    def encrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密配置
        
        Args:
            config: 配置字典
            
        Returns:
            加密后的配置字典
        """
        pass
    
    @abstractmethod
    def decrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密配置
        
        Args:
            config: 加密的配置字典
            
        Returns:
            解密后的配置字典
        """
        pass

class FernetEncryption(ConfigEncryption):
    """Fernet加密"""
    
    def __init__(self, key: Optional[bytes] = None, salt: Optional[bytes] = None):
        """
        初始化加密器
        
        Args:
            key: 密钥，如果为None则自动生成
            salt: 盐值，如果为None则自动生成
        """
        if key is None:
            key = Fernet.generate_key()
        if salt is None:
            salt = os.urandom(16)
        
        self.key = key
        self.salt = salt
        self.fernet = Fernet(key)
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> 'FernetEncryption':
        """
        从密码创建加密器
        
        Args:
            password: 密码
            salt: 盐值，如果为None则自动生成
            
        Returns:
            加密器实例
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return cls(key=key, salt=salt)
    
    def encrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密配置
        
        Args:
            config: 配置字典
            
        Returns:
            加密后的配置字典
        """
        try:
            # 序列化配置
            config_str = json.dumps(config)
            
            # 加密
            encrypted_data = self.fernet.encrypt(config_str.encode())
            
            return {
                "encrypted": True,
                "data": base64.b64encode(encrypted_data).decode(),
                "salt": base64.b64encode(self.salt).decode()
            }
            
        except Exception as e:
            logger.error(f"加密配置失败: {e}")
            raise
    
    def decrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密配置
        
        Args:
            config: 加密的配置字典
            
        Returns:
            解密后的配置字典
        """
        try:
            # 检查是否是加密的配置
            if not config.get("encrypted", False):
                return config
            
            # 解密
            encrypted_data = base64.b64decode(config["data"])
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # 反序列化
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"解密配置失败: {e}")
            raise

class AESEncryption(ConfigEncryption):
    """AES加密"""
    
    def __init__(self, key: Optional[bytes] = None, salt: Optional[bytes] = None):
        """
        初始化加密器
        
        Args:
            key: 密钥，如果为None则自动生成
            salt: 盐值，如果为None则自动生成
        """
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        if key is None:
            key = os.urandom(32)  # AES-256
        if salt is None:
            salt = os.urandom(16)
        
        self.key = key
        self.salt = salt
        self.cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(salt)
        )
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> 'AESEncryption':
        """
        从密码创建加密器
        
        Args:
            password: 密码
            salt: 盐值，如果为None则自动生成
            
        Returns:
            加密器实例
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = kdf.derive(password.encode())
        return cls(key=key, salt=salt)
    
    def encrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        加密配置
        
        Args:
            config: 配置字典
            
        Returns:
            加密后的配置字典
        """
        try:
            # 序列化配置
            config_str = json.dumps(config)
            
            # 填充
            from cryptography.hazmat.primitives import padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(config_str.encode()) + padder.finalize()
            
            # 加密
            encryptor = self.cipher.encryptor()
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                "encrypted": True,
                "algorithm": "AES",
                "data": base64.b64encode(encrypted_data).decode(),
                "salt": base64.b64encode(self.salt).decode()
            }
            
        except Exception as e:
            logger.error(f"加密配置失败: {e}")
            raise
    
    def decrypt(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解密配置
        
        Args:
            config: 加密的配置字典
            
        Returns:
            解密后的配置字���
        """
        try:
            # 检查是否是加密的配置
            if not config.get("encrypted", False):
                return config
            
            # 检查加密算法
            if config.get("algorithm") != "AES":
                raise ValueError("不支持的加密算法")
            
            # 解密
            encrypted_data = base64.b64decode(config["data"])
            decryptor = self.cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # 去除填充
            from cryptography.hazmat.primitives import padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            # 反序列化
            return json.loads(data.decode())
            
        except Exception as e:
            logger.error(f"解密配置失败: {e}")
            raise 