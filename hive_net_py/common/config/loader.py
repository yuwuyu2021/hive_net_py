"""
配置加载器模块
"""
import json
import logging
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ConfigLoader(ABC):
    """配置加载器基类"""
    
    @abstractmethod
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            配置字典
        """
        pass
    
    @abstractmethod
    def save(self, config: Dict[str, Any], file_path: str):
        """
        保存配置文件
        
        Args:
            config: 配置字典
            file_path: 配置文件路径
        """
        pass

class JSONConfigLoader(ConfigLoader):
    """JSON配置加载器"""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        加载JSON配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON配置文件失败: {e}")
            raise
    
    def save(self, config: Dict[str, Any], file_path: str):
        """
        保存JSON配置文件
        
        Args:
            config: 配置字典
            file_path: 配置文件路径
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存JSON配置文件失败: {e}")
            raise

class YAMLConfigLoader(ConfigLoader):
    """YAML配置加载器"""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载YAML配置文件失败: {e}")
            raise
    
    def save(self, config: Dict[str, Any], file_path: str):
        """
        保���YAML配置文件
        
        Args:
            config: 配置字典
            file_path: 配置文件路径
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, indent=2, allow_unicode=True)
        except Exception as e:
            logger.error(f"保存YAML配置文件失败: {e}")
            raise 