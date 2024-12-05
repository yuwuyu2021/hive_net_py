"""
配置模板模块
"""
from typing import Any, Dict, List, Optional, Set, Union
import re
from pathlib import Path
import copy
import jinja2
from jinja2 import Environment, FileSystemLoader

from .base import ConfigError, ConfigLoader


class TemplateError(ConfigError):
    """模板错误"""
    pass


class ConfigTemplate:
    """配置模板"""
    
    def __init__(
        self,
        template: Union[str, Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None,
        parent: Optional['ConfigTemplate'] = None
    ):
        """
        初始化模板
        
        Args:
            template: 模板内容(字符串或字典)
            variables: 变量字典
            parent: 父模板
        """
        self.template = template
        self.variables = variables or {}
        self.parent = parent
        self._env = Environment(
            loader=FileSystemLoader("."),
            undefined=jinja2.StrictUndefined
        )
    
    def render(self, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        渲染模板
        
        Args:
            variables: 额外的变量
        
        Returns:
            渲染后的配置
        """
        # 合并变量
        merged_vars = self.variables.copy()
        if variables:
            merged_vars.update(variables)
        
        try:
            # 如果模板是字符串,先渲染成字典
            if isinstance(self.template, str):
                template_str = self._env.from_string(self.template)
                config_str = template_str.render(**merged_vars)
                config = eval(config_str)  # 将字符串转换为字典
            else:
                config = self._render_dict(self.template, merged_vars)
            
            # 如果有父模板,先渲染父模板
            if self.parent:
                parent_config = self.parent.render(merged_vars)
                return self._merge_configs(parent_config, config)
            
            return config
        except Exception as e:
            raise TemplateError(f"Failed to render template: {e}")
    
    def _render_dict(
        self,
        template_dict: Dict[str, Any],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """渲染字典模板"""
        result = {}
        for key, value in template_dict.items():
            # 渲染键
            if isinstance(key, str):
                key_template = self._env.from_string(key)
                key = key_template.render(**variables)
            
            # 渲染值
            if isinstance(value, str):
                value_template = self._env.from_string(value)
                value = value_template.render(**variables)
            elif isinstance(value, dict):
                value = self._render_dict(value, variables)
            elif isinstance(value, list):
                value = self._render_list(value, variables)
            
            result[key] = value
        
        return result
    
    def _render_list(
        self,
        template_list: List[Any],
        variables: Dict[str, Any]
    ) -> List[Any]:
        """渲染列表模板"""
        result = []
        for item in template_list:
            if isinstance(item, str):
                item_template = self._env.from_string(item)
                item = item_template.render(**variables)
            elif isinstance(item, dict):
                item = self._render_dict(item, variables)
            elif isinstance(item, list):
                item = self._render_list(item, variables)
            result.append(item)
        return result
    
    def _merge_configs(
        self,
        parent: Dict[str, Any],
        child: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并配置"""
        result = copy.deepcopy(parent)
        
        def merge_dict(base: Dict[str, Any], update: Dict[str, Any]):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = copy.deepcopy(value)
        
        merge_dict(result, child)
        return result


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        初始化管理器
        
        Args:
            template_dir: 模板目录
        """
        self.template_dir = template_dir or Path("templates")
        self.templates: Dict[str, ConfigTemplate] = {}
        self._env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            undefined=jinja2.StrictUndefined
        )
    
    def load_template(
        self,
        name: str,
        loader: ConfigLoader,
        variables: Optional[Dict[str, Any]] = None,
        parent: Optional[str] = None
    ) -> ConfigTemplate:
        """
        加载模板
        
        Args:
            name: 模板名称
            loader: 配置加��器
            variables: 变量字典
            parent: 父模板名称
        
        Returns:
            配置模板
        """
        try:
            template_path = self.template_dir / name
            if not template_path.exists():
                raise TemplateError(f"Template not found: {name}")
            
            # 加载模板内容
            template_content = loader.load(template_path)
            
            # 获取父模板
            parent_template = None
            if parent:
                if parent not in self.templates:
                    raise TemplateError(f"Parent template not found: {parent}")
                parent_template = self.templates[parent]
            
            # 创建模板
            template = ConfigTemplate(
                template_content,
                variables,
                parent_template
            )
            
            self.templates[name] = template
            return template
        except Exception as e:
            raise TemplateError(f"Failed to load template: {e}")
    
    def get_template(self, name: str) -> ConfigTemplate:
        """
        获取模板
        
        Args:
            name: 模板名称
        
        Returns:
            配置模板
        """
        if name not in self.templates:
            raise TemplateError(f"Template not found: {name}")
        return self.templates[name]
    
    def render_template(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        渲染模板
        
        Args:
            name: 模板名称
            variables: 变量字典
        
        Returns:
            渲染后的配置
        """
        template = self.get_template(name)
        return template.render(variables)


class TemplateValidator:
    """模板验证器"""
    
    def __init__(self):
        self.required_variables: Set[str] = set()
    
    def validate(self, template: Union[str, Dict[str, Any]]) -> List[str]:
        """
        验证模板
        
        Args:
            template: 模板内容
        
        Returns:
            所需变量列表
        """
        self.required_variables.clear()
        
        if isinstance(template, str):
            self._validate_string(template)
        elif isinstance(template, dict):
            self._validate_dict(template)
        
        return list(self.required_variables)
    
    def _validate_string(self, template: str):
        """验证字符串模板"""
        # 查找 {{ variable }} 形式的变量
        pattern = r'{{\s*(\w+)\s*}}'
        matches = re.finditer(pattern, template)
        for match in matches:
            self.required_variables.add(match.group(1))
    
    def _validate_dict(self, template: Dict[str, Any]):
        """验证字典模板"""
        for key, value in template.items():
            if isinstance(key, str):
                self._validate_string(key)
            
            if isinstance(value, str):
                self._validate_string(value)
            elif isinstance(value, dict):
                self._validate_dict(value)
            elif isinstance(value, list):
                self._validate_list(value)
    
    def _validate_list(self, template: List[Any]):
        """验证列表模板"""
        for item in template:
            if isinstance(item, str):
                self._validate_string(item)
            elif isinstance(item, dict):
                self._validate_dict(item)
            elif isinstance(item, list):
                self._validate_list(item) 