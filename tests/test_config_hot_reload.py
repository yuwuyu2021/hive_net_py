"""
测试配置热重载功能
"""
import asyncio
import json
import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from hive_net_py.common.config.hot_reload import ConfigHotReload
from hive_net_py.common.config.loader import JSONConfigLoader
from hive_net_py.common.config.validator import ConfigValidator
from hive_net_py.common.config.encryption import ConfigEncryption

@pytest.fixture
def config_dir():
    """创建临时配置目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def config_file(config_dir):
    """创建测试配置文件"""
    config = {
        "name": "test",
        "version": "1.0.0",
        "settings": {
            "debug": True,
            "port": 8080
        }
    }
    
    file_path = Path(config_dir) / "config.json"
    with open(file_path, "w") as f:
        json.dump(config, f)
    
    return str(file_path)

@pytest.fixture
def loader():
    """创建配置加载器"""
    return JSONConfigLoader()

@pytest.fixture
def validator():
    """创建配置验证器"""
    validator = MagicMock(spec=ConfigValidator)
    validator.validate = MagicMock()
    return validator

@pytest.fixture
def encryption():
    """创建配置加密器"""
    encryption = MagicMock(spec=ConfigEncryption)
    encryption.decrypt = MagicMock(return_value={"decrypted": True})
    return encryption

@pytest.fixture
async def hot_reload(config_dir, loader, validator, encryption):
    """创建热重载器"""
    reload = ConfigHotReload(
        config_dir=config_dir,
        loader=loader,
        validator=validator,
        encryption=encryption
    )
    try:
        return reload
    finally:
        await reload.stop()

@pytest.mark.asyncio
async def test_hot_reload_start_stop(hot_reload):
    """测试启动和停止"""
    hot_reload = await hot_reload
    assert not hot_reload.is_running
    
    await hot_reload.start()
    assert hot_reload.is_running
    
    await hot_reload.stop()
    assert not hot_reload.is_running

@pytest.mark.asyncio
async def test_add_remove_watch(hot_reload, config_file):
    """测试添加和移除监视"""
    hot_reload = await hot_reload
    handler = MagicMock()
    config_name = Path(config_file).name
    
    # 添加监视
    hot_reload.add_watch(config_name, handler)
    assert str(Path(config_file)) in hot_reload._handlers
    
    # 移除监视
    hot_reload.remove_watch(config_name)
    assert str(Path(config_file)) not in hot_reload._handlers

@pytest.mark.asyncio
async def test_config_change_handler(hot_reload, config_file):
    """测试配置变更处理"""
    hot_reload = await hot_reload
    handler = MagicMock()
    config_name = Path(config_file).name
    
    # 添加监视
    hot_reload.add_watch(config_name, handler)
    await hot_reload.start()
    
    # 修改配置文件
    new_config = {
        "name": "test_modified",
        "version": "1.1.0",
        "settings": {
            "debug": False,
            "port": 9090
        }
    }
    
    with open(config_file, "w") as f:
        json.dump(new_config, f)
    
    # 等待文件系统事件
    await asyncio.sleep(2)
    
    # 验证处理函数被调用
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_config_validation(hot_reload, config_file, validator):
    """测试配置验证"""
    hot_reload = await hot_reload
    handler = MagicMock()
    config_name = Path(config_file).name
    
    # 添加监视
    hot_reload.add_watch(config_name, handler)
    await hot_reload.start()
    
    # 修改配置文件
    new_config = {"invalid": True}
    with open(config_file, "w") as f:
        json.dump(new_config, f)
    
    # 等待文件系统事件
    await asyncio.sleep(2)
    
    # 验证配置验证器被调用
    validator.validate.assert_called_once()

@pytest.mark.asyncio
async def test_config_decryption(hot_reload, config_file, encryption):
    """测试配置解密"""
    hot_reload = await hot_reload
    handler = MagicMock()
    config_name = Path(config_file).name
    
    # 添加监视
    hot_reload.add_watch(config_name, handler)
    await hot_reload.start()
    
    # 修改配置文件
    new_config = {"encrypted": True}
    with open(config_file, "w") as f:
        json.dump(new_config, f)
    
    # 等待文件系统事件
    await asyncio.sleep(2)
    
    # 验证配置解密器被调用
    encryption.decrypt.assert_called_once()

@pytest.mark.asyncio
async def test_invalid_config_file(hot_reload):
    """测试无效配置文件"""
    hot_reload = await hot_reload
    with pytest.raises(FileNotFoundError):
        hot_reload.add_watch("invalid.json", MagicMock())

@pytest.mark.asyncio
async def test_cooldown_period(hot_reload, config_file):
    """测试冷却时间"""
    hot_reload = await hot_reload
    handler = MagicMock()
    config_name = Path(config_file).name
    
    # 添加监视
    hot_reload.add_watch(config_name, handler)
    await hot_reload.start()
    
    # 快速修改配置文件多次
    for i in range(3):
        new_config = {"version": f"1.0.{i}"}
        with open(config_file, "w") as f:
            json.dump(new_config, f)
        await asyncio.sleep(0.1)
    
    # 等待文件系统事件
    await asyncio.sleep(2)
    
    # 验证处理函数只被调用一次
    assert handler.call_count == 1 