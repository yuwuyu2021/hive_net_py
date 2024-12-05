"""
配置模板测试
"""
import pytest
from pathlib import Path
from typing import Dict, Any

from hive_net_py.common.config.template import (
    TemplateError,
    ConfigTemplate,
    TemplateManager,
    TemplateValidator
)
from hive_net_py.common.config.base import JSONConfigLoader


@pytest.fixture
def template_dict() -> Dict[str, Any]:
    """测试用模板字典"""
    return {
        'network': {
            'host': '{{ host }}',
            'port': '{{ port }}',
            'timeout': '{{ timeout }}'
        },
        'security': {
            'enabled': '{{ security_enabled }}',
            'token': '{{ security_token }}',
            'level': '{{ security_level }}'
        },
        'logging': {
            'level': '{{ log_level }}',
            'file': 'logs/{{ app_name }}.log'
        }
    }


@pytest.fixture
def template_str() -> str:
    """测试用模板字符串"""
    return """
    {
        'network': {
            'host': '{{ host }}',
            'port': {{ port }},
            'timeout': {{ timeout }}
        },
        'security': {
            'enabled': {{ security_enabled }},
            'token': '{{ security_token }}',
            'level': {{ security_level }}
        }
    }
    """


@pytest.fixture
def template_variables() -> Dict[str, Any]:
    """测试用变量字典"""
    return {
        'host': '127.0.0.1',
        'port': 8080,
        'timeout': 30,
        'security_enabled': True,
        'security_token': 'abc123',
        'security_level': 2,
        'log_level': 'INFO',
        'app_name': 'myapp'
    }


def test_config_template_dict(template_dict, template_variables):
    """测试字典模板"""
    template = ConfigTemplate(template_dict)
    config = template.render(template_variables)
    
    assert config['network']['host'] == '127.0.0.1'
    assert config['network']['port'] == '8080'
    assert config['security']['enabled'] == 'True'
    assert config['logging']['file'] == 'logs/myapp.log'


def test_config_template_str(template_str, template_variables):
    """测试字符串模板"""
    template = ConfigTemplate(template_str)
    config = template.render(template_variables)
    
    assert config['network']['host'] == '127.0.0.1'
    assert config['network']['port'] == 8080
    assert config['security']['enabled'] is True
    assert config['security']['level'] == 2


def test_template_inheritance():
    """���试模板继承"""
    # 创建父模板
    parent_template = ConfigTemplate({
        'database': {
            'host': '{{ db_host }}',
            'port': '{{ db_port }}',
            'name': '{{ db_name }}'
        },
        'cache': {
            'enabled': '{{ cache_enabled }}',
            'size': '{{ cache_size }}'
        }
    })
    
    # 创建子模板
    child_template = ConfigTemplate({
        'database': {
            'username': '{{ db_user }}',
            'password': '{{ db_pass }}'
        },
        'cache': {
            'type': '{{ cache_type }}'
        }
    }, parent=parent_template)
    
    # 渲染模板
    variables = {
        'db_host': 'localhost',
        'db_port': 5432,
        'db_name': 'mydb',
        'db_user': 'admin',
        'db_pass': 'secret',
        'cache_enabled': True,
        'cache_size': 1000,
        'cache_type': 'redis'
    }
    
    config = child_template.render(variables)
    
    # 验证结果
    assert config['database']['host'] == 'localhost'
    assert config['database']['username'] == 'admin'
    assert config['cache']['enabled'] == 'True'
    assert config['cache']['type'] == 'redis'


def test_template_manager(tmp_path, template_dict, template_variables):
    """测试模板管理器"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板文件
    template_path = template_dir / 'config.json'
    loader = JSONConfigLoader()
    loader.save(template_dict, template_path)
    
    # 创建模板管理器
    manager = TemplateManager(template_dir)
    
    # 加载并渲染模板
    template = manager.load_template('config.json', loader)
    config = manager.render_template('config.json', template_variables)
    
    assert config['network']['host'] == '127.0.0.1'
    assert config['security']['token'] == 'abc123'
    assert config['logging']['file'] == 'logs/myapp.log'


def test_template_validator(template_dict):
    """测试模板验证器"""
    validator = TemplateValidator()
    required_vars = validator.validate(template_dict)
    
    # 验证必需变量
    assert 'host' in required_vars
    assert 'port' in required_vars
    assert 'security_token' in required_vars
    assert 'app_name' in required_vars
    
    # 验证变量数量
    assert len(required_vars) == 8


def test_missing_variables(template_dict):
    """测试缺失变量"""
    template = ConfigTemplate(template_dict)
    
    # 缺少必需变量
    with pytest.raises(TemplateError):
        template.render({'host': '127.0.0.1'})  # 缺少其他变量


def test_invalid_template():
    """测试无效模板"""
    # 无效的模板字符串
    with pytest.raises(TemplateError):
        template = ConfigTemplate("{invalid")
        template.render({})
    
    # 无效的变量名
    with pytest.raises(TemplateError):
        template = ConfigTemplate("{{ invalid-name }}")
        template.render({})


def test_template_manager_errors(tmp_path):
    """测试模板管理器错误处理"""
    manager = TemplateManager(tmp_path)
    
    # 测试不存在的模板
    with pytest.raises(TemplateError):
        manager.get_template('non_existent.json')
    
    # 测试无效的父模板
    with pytest.raises(TemplateError):
        manager.load_template(
            'child.json',
            JSONConfigLoader(),
            parent='non_existent.json'
        ) 