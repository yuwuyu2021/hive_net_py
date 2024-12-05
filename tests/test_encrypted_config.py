"""
加密配置加载器测试
"""
import pytest
from pathlib import Path
import json
import yaml

from hive_net_py.common.config.encrypted import (
    generate_key,
    EncryptedConfigLoader,
    create_encrypted_loader,
    ConfigError
)
from hive_net_py.common.config.base import JSONConfigLoader, YAMLConfigLoader


@pytest.fixture
def test_password():
    """测试用密码"""
    return "test_password_123"


@pytest.fixture
def json_config():
    """测试用JSON配置"""
    return {
        "test_key": "test_value",
        "nested": {
            "key": "value"
        }
    }


@pytest.fixture
def yaml_config():
    """测试用YAML配置"""
    return {
        "test_key": "test_value",
        "list": ["item1", "item2"],
        "nested": {
            "key": "value"
        }
    }


def test_generate_key(test_password):
    """测试密钥生成"""
    key1 = generate_key(test_password)
    key2 = generate_key(test_password)
    assert key1 == key2  # 相同密码应生成相同密钥
    
    key3 = generate_key(test_password + "different")
    assert key1 != key3  # 不同密码应生成不同密钥
    
    key4 = generate_key(test_password, salt=b"different_salt")
    assert key1 != key4  # 不同盐值应生成不同密钥


def test_encrypted_json_config(tmp_path, test_password, json_config):
    """测试JSON加密配置"""
    config_file = tmp_path / "config.json.enc"
    loader = create_encrypted_loader("json", test_password)
    
    # 保存加密配置
    loader.save(json_config, config_file)
    assert config_file.exists()
    
    # 验证文件已加密
    with open(config_file, 'rb') as f:
        encrypted_data = f.read()
    with pytest.raises(json.JSONDecodeError):
        json.loads(encrypted_data)
    
    # 加载并验证配置
    loaded_config = loader.load(config_file)
    assert loaded_config == json_config


def test_encrypted_yaml_config(tmp_path, test_password, yaml_config):
    """测试YAML加密配置"""
    config_file = tmp_path / "config.yml.enc"
    loader = create_encrypted_loader("yaml", test_password)
    
    # 保存加密配置
    loader.save(yaml_config, config_file)
    assert config_file.exists()
    
    # 验证文件已加密
    with open(config_file, 'rb') as f:
        encrypted_data = f.read()
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load(encrypted_data)
    
    # 加载并验证配置
    loaded_config = loader.load(config_file)
    assert loaded_config == yaml_config


def test_wrong_password(tmp_path, test_password, json_config):
    """测试错误密码"""
    config_file = tmp_path / "config.json.enc"
    
    # 使用正确密码保存
    loader = create_encrypted_loader("json", test_password)
    loader.save(json_config, config_file)
    
    # 使用错误密码加载
    wrong_loader = create_encrypted_loader("json", "wrong_password")
    with pytest.raises(ConfigError):
        wrong_loader.load(config_file)


def test_file_tampering(tmp_path, test_password, json_config):
    """测试文件篡改"""
    config_file = tmp_path / "config.json.enc"
    
    # 保存配置
    loader = create_encrypted_loader("json", test_password)
    loader.save(json_config, config_file)
    
    # 篡改文件
    with open(config_file, 'rb') as f:
        data = f.read()
    with open(config_file, 'wb') as f:
        f.write(data[:-1] + b'X')  # 修改最后一个字节
    
    # 尝试加载被篡改的文件
    with pytest.raises(ConfigError):
        loader.load(config_file)


def test_unsupported_file_type(test_password):
    """测试不支持的文件类型"""
    with pytest.raises(ConfigError):
        create_encrypted_loader("invalid", test_password) 