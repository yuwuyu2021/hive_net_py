"""
加密模板测试
"""
import pytest
from pathlib import Path
from typing import Dict, Any

from hive_net_py.common.config.encrypted_template import (
    EncryptedTemplate,
    EncryptedTemplateManager,
    TemplateError
)
from hive_net_py.common.config.base import JSONConfigLoader, YAMLConfigLoader


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
        }
    }


@pytest.fixture
def template_variables() -> Dict[str, Any]:
    """测试用变量字典"""
    return {
        'host': '127.0.0.1',
        'port': 8080,
        'timeout': 30,
        'security_enabled': True,
        'security_token': 'abc123',
        'security_level': 2
    }


@pytest.fixture
def test_password() -> str:
    """测试用密码"""
    return "test_password_123"


def test_encrypted_template(tmp_path, template_dict, template_variables, test_password):
    """测试加密模板"""
    # 创建加密模板
    template = EncryptedTemplate(
        template_dict,
        test_password,
        template_variables
    )
    
    # 保存模板
    template_path = tmp_path / "config.json"
    template.save(template_path, JSONConfigLoader())
    
    # 验证文件已加密
    with open(template_path, 'rb') as f:
        encrypted_data = f.read()
    assert b'{"network":' not in encrypted_data
    
    # 渲染模板
    config = template.render()
    assert config['network']['host'] == '127.0.0.1'
    assert config['security']['token'] == 'abc123'


def test_encrypted_template_manager(tmp_path, template_dict, template_variables, test_password):
    """测试加密模板管理器"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板管理器
    manager = EncryptedTemplateManager(template_dir, test_password)
    
    # 保存加密模板
    manager.save_encrypted_template(
        'config.json',
        template_dict,
        JSONConfigLoader(),
        variables=template_variables
    )
    
    # 加载加密模板
    template = manager.load_encrypted_template(
        'config.json',
        JSONConfigLoader()
    )
    
    # 渲染模板
    config = template.render()
    assert config['network']['host'] == '127.0.0.1'
    assert config['security']['token'] == 'abc123'


def test_template_encryption(tmp_path, template_dict, template_variables, test_password):
    """测试模板加密"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板管理器
    manager = EncryptedTemplateManager(template_dir, test_password)
    
    # 保存普通模板
    template_path = template_dir / 'config.json'
    loader = JSONConfigLoader()
    loader.save(template_dict, template_path)
    
    # 加载普通模板
    template = manager.load_template('config.json', loader)
    
    # 加密模板
    manager.encrypt_existing_template('config.json')
    assert manager.is_encrypted('config.json')
    
    # 验证加密后的模板
    encrypted_template = manager.get_template('config.json')
    config = encrypted_template.render(template_variables)
    assert config['network']['host'] == '127.0.0.1'
    assert config['security']['token'] == 'abc123'


def test_template_decryption(tmp_path, template_dict, template_variables, test_password):
    """测试模板解密"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板管理器
    manager = EncryptedTemplateManager(template_dir, test_password)
    
    # 保存加密模板
    manager.save_encrypted_template(
        'config.json',
        template_dict,
        JSONConfigLoader(),
        variables=template_variables
    )
    
    # 解密模板
    manager.decrypt_template('config.json')
    assert not manager.is_encrypted('config.json')
    
    # 验证解密后的模板
    template = manager.get_template('config.json')
    config = template.render(template_variables)
    assert config['network']['host'] == '127.0.0.1'
    assert config['security']['token'] == 'abc123'


def test_encrypted_template_inheritance(tmp_path, test_password):
    """测试加密模板继承"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板管理器
    manager = EncryptedTemplateManager(template_dir, test_password)
    
    # 创建父模板
    parent_template = {
        'database': {
            'host': '{{ db_host }}',
            'port': '{{ db_port }}'
        },
        'cache': {
            'enabled': '{{ cache_enabled }}'
        }
    }
    
    # 创建子模板
    child_template = {
        'database': {
            'username': '{{ db_user }}',
            'password': '{{ db_pass }}'
        }
    }
    
    # 保存父模板
    manager.save_encrypted_template(
        'parent.json',
        parent_template,
        JSONConfigLoader()
    )
    
    # 保存子模板
    manager.save_encrypted_template(
        'child.json',
        child_template,
        JSONConfigLoader(),
        parent='parent.json'
    )
    
    # 渲染子模板
    variables = {
        'db_host': 'localhost',
        'db_port': 5432,
        'db_user': 'admin',
        'db_pass': 'secret',
        'cache_enabled': True
    }
    
    template = manager.get_template('child.json')
    config = template.render(variables)
    
    assert config['database']['host'] == 'localhost'
    assert config['database']['username'] == 'admin'
    assert config['cache']['enabled'] == 'True'


def test_encrypted_template_errors(tmp_path, template_dict, test_password):
    """测试加密模板错误处理"""
    # 创建模板目录
    template_dir = tmp_path / 'templates'
    template_dir.mkdir()
    
    # 创建模板管理器
    manager = EncryptedTemplateManager(template_dir)
    
    # 测试缺少密码
    with pytest.raises(TemplateError):
        manager.save_encrypted_template(
            'config.json',
            template_dict,
            JSONConfigLoader()
        )
    
    # 测试加载不存在的模板
    with pytest.raises(TemplateError):
        manager.load_encrypted_template(
            'non_existent.json',
            JSONConfigLoader(),
            test_password
        )
    
    # 测试加密已加密的模板
    manager.save_encrypted_template(
        'config.json',
        template_dict,
        JSONConfigLoader(),
        test_password
    )
    
    with pytest.raises(TemplateError):
        manager.encrypt_existing_template('config.json', test_password)
    
    # 测试解密未加密的模板
    template_path = template_dir / 'plain.json'
    loader = JSONConfigLoader()
    loader.save(template_dict, template_path)
    manager.load_template('plain.json', loader)
    
    with pytest.raises(TemplateError):
        manager.decrypt_template('plain.json', test_password)
    
    # 测试使用错误密码解密
    with pytest.raises(TemplateError):
        manager.decrypt_template('config.json', 'wrong_password') 