"""
配置验证器模块
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

class ConfigValidator(ABC):
    """配置验证器基类"""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
            
        Raises:
            ValidationError: 验证失败时抛出
        """
        pass

class JSONSchemaValidator(ConfigValidator):
    """JSON Schema验证器"""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        初始化验证器
        
        Args:
            schema: JSON Schema
        """
        self.schema = schema
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        使用JSON Schema验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
            
        Raises:
            ValidationError: 验证失败时抛出
        """
        try:
            validate(instance=config, schema=self.schema)
            return True
        except ValidationError as e:
            logger.error(f"配置验证失败: {e}")
            raise

class RuleBasedValidator(ConfigValidator):
    """基于规则的验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self._rules: List[ValidationRule] = []
    
    def add_rule(self, rule: 'ValidationRule'):
        """
        添加验证规则
        
        Args:
            rule: 验证规则
        """
        self._rules.append(rule)
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
            
        Raises:
            ValidationError: 验证失败时抛出
        """
        for rule in self._rules:
            if not rule.validate(config):
                raise ValidationError(f"规则验证失败: {rule.name}")
        return True

class ValidationRule(ABC):
    """验证规则基类"""
    
    def __init__(self, name: str):
        """
        初始化规则
        
        Args:
            name: 规则名称
        """
        self.name = name
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        pass

class RequiredFieldsRule(ValidationRule):
    """必填字段规则"""
    
    def __init__(self, fields: Set[str]):
        """
        初始化规则
        
        Args:
            fields: 必填字段集合
        """
        super().__init__("必填字段规则")
        self.fields = fields
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证必填字段
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        for field in self.fields:
            if field not in config:
                return False
        return True

class TypeCheckRule(ValidationRule):
    """类型检查规则"""
    
    def __init__(self, type_map: Dict[str, type]):
        """
        初始化规则
        
        Args:
            type_map: 字段类型映射
        """
        super().__init__("类型检查规则")
        self.type_map = type_map
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证字段类型
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        for field, expected_type in self.type_map.items():
            if field in config and not isinstance(config[field], expected_type):
                return False
        return True

class RangeCheckRule(ValidationRule):
    """范围检查规则"""
    
    def __init__(self, ranges: Dict[str, tuple]):
        """
        初始化规则
        
        Args:
            ranges: 字段范围映射，格式为 {字段名: (最小值, 最大值)}
        """
        super().__init__("范围检查规则")
        self.ranges = ranges
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证字段范围
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        for field, (min_val, max_val) in self.ranges.items():
            if field in config:
                value = config[field]
                if not (min_val <= value <= max_val):
                    return False
        return True

class RegexCheckRule(ValidationRule):
    """正则表达式检查规则"""
    
    def __init__(self, patterns: Dict[str, str]):
        """
        初始化规则
        
        Args:
            patterns: 字段正则表达式映射
        """
        super().__init__("正则表达式检查规则")
        self.patterns = patterns
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证字段格式
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        import re
        for field, pattern in self.patterns.items():
            if field in config:
                value = str(config[field])
                if not re.match(pattern, value):
                    return False
        return True

class DependencyCheckRule(ValidationRule):
    """依赖检查规则"""
    
    def __init__(self, dependencies: Dict[str, Set[str]]):
        """
        初始化规则
        
        Args:
            dependencies: 字段依赖映射，格式为 {字段名: {依赖字段集合}}
        """
        super().__init__("依赖检查规则")
        self.dependencies = dependencies
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证字段依赖
        
        Args:
            config: 配置字典
            
        Returns:
            验证是否通过
        """
        for field, deps in self.dependencies.items():
            if field in config:
                for dep in deps:
                    if dep not in config:
                        return False
        return True