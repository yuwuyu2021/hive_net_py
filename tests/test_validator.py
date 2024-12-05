"""
配置验证器测试
"""
import re
import pytest
from typing import Any, Dict

from hive_net_py.common.config.validator import (
    ValidationError,
    ValidationRule,
    RequiredFieldsRule,
    TypeCheckRule,
    RangeCheckRule,
    PatternMatchRule,
    CustomRule,
    CompositeValidator,
    SchemaValidator
)


def test_required_fields_rule():
    """测试必填字段规则"""
    # 创建规则
    rule = RequiredFieldsRule({'name', 'age', 'email'})
    
    # 测试有效配置
    valid_config = {
        'name': 'Test User',
        'age': 25,
        'email': 'test@example.com',
        'optional': 'value'
    }
    assert rule.validate(valid_config)
    
    # 测试缺少字段
    invalid_config = {
        'name': 'Test User',
        'age': 25
    }
    assert not rule.validate(invalid_config)
    error_message = rule.get_error_message(invalid_config)
    assert 'email' in error_message
    
    # 测试空值
    null_config = {
        'name': 'Test User',
        'age': None,
        'email': 'test@example.com'
    }
    assert not rule.validate(null_config)
    error_message = rule.get_error_message(null_config)
    assert 'age' in error_message


def test_type_check_rule():
    """测试类型检查规则"""
    # 创建规则
    rule = TypeCheckRule({
        'name': str,
        'age': int,
        'score': float,
        'active': bool
    })
    
    # 测试有效配置
    valid_config = {
        'name': 'Test User',
        'age': 25,
        'score': 95.5,
        'active': True
    }
    assert rule.validate(valid_config)
    
    # 测试类型错误
    invalid_config = {
        'name': 'Test User',
        'age': '25',  # 应该是int
        'score': 95.5,
        'active': True
    }
    assert not rule.validate(invalid_config)
    error_message = rule.get_error_message(invalid_config)
    assert 'age' in error_message
    assert 'str' in error_message
    assert 'int' in error_message


def test_range_check_rule():
    """测试范围检查规则"""
    # 创建规则
    rule = RangeCheckRule({
        'age': (0, 150),
        'score': (0.0, 100.0),
        'quantity': (1, None),  # 只有最小值
        'percent': (None, 1.0)  # 只有最大值
    })
    
    # 测试有效配置
    valid_config = {
        'age': 25,
        'score': 95.5,
        'quantity': 10,
        'percent': 0.5
    }
    assert rule.validate(valid_config)
    
    # 测试超出范围
    invalid_config = {
        'age': -1,
        'score': 101.0,
        'quantity': 0,
        'percent': 1.5
    }
    assert not rule.validate(invalid_config)
    error_message = rule.get_error_message(invalid_config)
    assert 'age' in error_message
    assert 'score' in error_message
    assert 'quantity' in error_message
    assert 'percent' in error_message


def test_pattern_match_rule():
    """测试正则表达式匹配规则"""
    # 创建规则
    rule = PatternMatchRule({
        'email': r'^[\w\.-]+@[\w\.-]+\.\w+$',
        'phone': r'^\d{11}$',
        'username': re.compile(r'^[a-zA-Z]\w{2,19}$')
    })
    
    # 测试有效配置
    valid_config = {
        'email': 'test@example.com',
        'phone': '13800138000',
        'username': 'user123'
    }
    assert rule.validate(valid_config)
    
    # 测试不匹配
    invalid_config = {
        'email': 'invalid-email',
        'phone': '1234',
        'username': '123user'
    }
    assert not rule.validate(invalid_config)
    error_message = rule.get_error_message(invalid_config)
    assert 'email' in error_message
    assert 'phone' in error_message
    assert 'username' in error_message


def test_custom_rule():
    """测试自定义规则"""
    # 创建自定义验证函数
    def validate_password(value: str) -> bool:
        return (
            len(value) >= 8 and
            any(c.isupper() for c in value) and
            any(c.islower() for c in value) and
            any(c.isdigit() for c in value)
        )
    
    def password_error_message(value: str) -> str:
        errors = []
        if len(value) < 8:
            errors.append("at least 8 characters")
        if not any(c.isupper() for c in value):
            errors.append("at least one uppercase letter")
        if not any(c.islower() for c in value):
            errors.append("at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            errors.append("at least one digit")
        return f"Password must contain {', '.join(errors)}"
    
    # 创建规则
    rule = CustomRule(validate_password, password_error_message)
    
    # 测试有效密码
    assert rule.validate("Password123")
    
    # 测试无效密码
    invalid_password = "password"
    assert not rule.validate(invalid_password)
    error_message = rule.get_error_message(invalid_password)
    assert "uppercase letter" in error_message
    assert "digit" in error_message


def test_composite_validator():
    """测试组合验证器"""
    # 创建验证规则
    required_rule = RequiredFieldsRule({'username', 'email', 'age'})
    type_rule = TypeCheckRule({
        'username': str,
        'email': str,
        'age': int
    })
    range_rule = RangeCheckRule({
        'age': (0, 150)
    })
    pattern_rule = PatternMatchRule({
        'email': r'^[\w\.-]+@[\w\.-]+\.\w+$'
    })
    
    # 创建组合验证器
    validator = CompositeValidator([
        required_rule,
        type_rule,
        range_rule,
        pattern_rule
    ])
    
    # 测试有效配置
    valid_config = {
        'username': 'testuser',
        'email': 'test@example.com',
        'age': 25
    }
    validator.validate(valid_config)  # 不应抛出异常
    
    # 测试无效配置
    invalid_config = {
        'username': 'testuser',
        'email': 'invalid-email',
        'age': -1
    }
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(invalid_config)
    error_message = str(exc_info.value)
    assert 'email' in error_message
    assert 'age' in error_message


def test_schema_validator():
    """测试模式验证器"""
    # 创建模式
    schema = {
        'username': {
            'type': str,
            'required': True,
            'pattern': r'^[a-zA-Z]\w{2,19}$'
        },
        'email': {
            'type': str,
            'required': True,
            'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'
        },
        'age': {
            'type': int,
            'required': True,
            'min': 0,
            'max': 150
        },
        'score': {
            'type': float,
            'required': False,
            'min': 0.0,
            'max': 100.0
        },
        'password': {
            'type': str,
            'required': True,
            'custom': lambda v: (
                len(v) >= 8 and
                any(c.isupper() for c in v) and
                any(c.islower() for c in v) and
                any(c.isdigit() for c in v)
            )
        }
    }
    
    # 创建验证器
    validator = SchemaValidator(schema)
    
    # 测试有效配置
    valid_config = {
        'username': 'testuser',
        'email': 'test@example.com',
        'age': 25,
        'score': 95.5,
        'password': 'Password123'
    }
    assert validator.validate(valid_config)
    
    # 测试无效配置
    invalid_config = {
        'username': '123user',  # 无效用户名
        'email': 'invalid-email',  # 无效邮箱
        'age': -1,  # 无效年龄
        'score': 101.0,  # 无效分数
        'password': 'password'  # 无效密码
    }
    assert not validator.validate(invalid_config)
    error_message = validator.get_error_message(invalid_config)
    assert 'username' in error_message
    assert 'email' in error_message
    assert 'age' in error_message
    assert 'score' in error_message
    assert 'password' in error_message


def test_schema_validator_with_missing_fields():
    """测试模式验证器处理缺失字段"""
    # 创建模式
    schema = {
        'required_field': {
            'type': str,
            'required': True
        },
        'optional_field': {
            'type': str,
            'required': False
        }
    }
    
    # 创建验证器
    validator = SchemaValidator(schema)
    
    # 测试缺少必填字段
    invalid_config = {
        'optional_field': 'value'
    }
    assert not validator.validate(invalid_config)
    error_message = validator.get_error_message(invalid_config)
    assert 'required_field' in error_message
    
    # 测试缺少可选字段
    valid_config = {
        'required_field': 'value'
    }
    assert validator.validate(valid_config)


def test_schema_validator_with_invalid_types():
    """测试模式验证器处理类型错误"""
    # 创建模式
    schema = {
        'string_field': {'type': str},
        'int_field': {'type': int},
        'float_field': {'type': float},
        'bool_field': {'type': bool}
    }
    
    # 创建验证器
    validator = SchemaValidator(schema)
    
    # 测试类型错误
    invalid_config = {
        'string_field': 123,
        'int_field': '123',
        'float_field': True,
        'bool_field': 'true'
    }
    assert not validator.validate(invalid_config)
    error_message = validator.get_error_message(invalid_config)
    assert 'string_field' in error_message
    assert 'int_field' in error_message
    assert 'float_field' in error_message
    assert 'bool_field' in error_message
  