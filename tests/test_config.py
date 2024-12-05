"""
配置管理模块测试
"""
import pytest
from pathlib import Path
import json
import yaml
from typing import Dict, Any

from hive_net_py.common.config.base import (
    ConfigError,
    ConfigValidator,
    JSONConfigLoader,
    YAMLConfigLoader,
    ConfigManager
)


class TestValidator(ConfigValidator):
    """测试用验证器"""
    def validate(self, config: Dict[str, Any]) -> bool:
        return isinstance(config, dict) and 'test_key' in config


@pytest.fixture
def json_config_file(tmp_path):
    """创建测试用JSON配置文件"""
    config_file = tmp_path / "test_config.json"
    config = {"test_key": "test_value"}
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def yaml_config_file(tmp_path):
    """创建测试用YAML配置文件"""
    config_file = tmp_path / "test_config.yml"
    config = {"test_key": "test_value"}
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)
    return config_file


def test_json_config_loader(json_config_file):
    """测试JSON配置加载器"""
    loader = JSONConfigLoader()
    config = loader.load(json_config_file)
    assert config["test_key"] == "test_value"

    new_config = {"new_key": "new_value"}
    loader.save(new_config, json_config_file)
    loaded_config = loader.load(json_config_file)
    assert loaded_config["new_key"] == "new_value"


def test_yaml_config_loader(yaml_config_file):
    """测试YAML配置加载器"""
    loader = YAMLConfigLoader()
    config = loader.load(yaml_config_file)
    assert config["test_key"] == "test_value"

    new_config = {"new_key": "new_value"}
    loader.save(new_config, yaml_config_file)
    loaded_config = loader.load(yaml_config_file)
    assert loaded_config["new_key"] == "new_value"


def test_config_manager_json(json_config_file):
    """测试JSON配置管理器"""
    validator = TestValidator()
    manager = ConfigManager(json_config_file, validator=validator)
    
    assert manager.get("test_key") == "test_value"
    assert manager.get("non_exist", "default") == "default"

    manager.set("new_key", "new_value")
    assert manager.get("new_key") == "new_value"

    manager.reload()
    assert manager.get("new_key") == "new_value"


def test_config_manager_yaml(yaml_config_file):
    """测试YAML配置��理器"""
    validator = TestValidator()
    manager = ConfigManager(yaml_config_file, validator=validator)
    
    assert manager.get("test_key") == "test_value"
    assert manager.get("non_exist", "default") == "default"

    manager.set("new_key", "new_value")
    assert manager.get("new_key") == "new_value"

    manager.reload()
    assert manager.get("new_key") == "new_value"


def test_config_validation():
    """测试配置验证"""
    validator = TestValidator()
    config_file = Path("test_config.json")
    
    # 创建无效配置
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump({"invalid_key": "value"}, f)
    
    with pytest.raises(ConfigError):
        ConfigManager(config_file, validator=validator)
    
    # 清理测试文件
    config_file.unlink()


def test_unsupported_config_type(tmp_path):
    """测试不支持的配置文件类型"""
    config_file = tmp_path / "test.txt"
    config_file.touch()
    
    with pytest.raises(ConfigError):
        ConfigManager(config_file) 