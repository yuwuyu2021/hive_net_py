"""
告警处理器测试
"""
import json
import base64
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from datetime import datetime

from hive_net_py.client.core.event_monitor import Alert, AlertLevel
from hive_net_py.client.core.alert_handlers import (
    SMTPConfig,
    EmailAlertHandler,
    WeChatWorkConfig,
    WeChatWorkAlertHandler,
    DingTalkConfig,
    DingTalkAlertHandler,
    FeishuConfig,
    FeishuAlertHandler,
    SMSConfig,
    SMSAlertHandler,
    CompositeAlertHandler
)


@pytest.fixture
def test_alert():
    """测试用告警"""
    return Alert(
        rule_name="test_rule",
        level=AlertLevel.ERROR,
        message="Test alert message",
        source="test_source",
        timestamp=datetime.now().timestamp(),
        events=[],
        context={}
    )


@pytest.fixture
def smtp_config():
    """SMTP配置"""
    return SMTPConfig(
        host="smtp.example.com",
        port=587,
        username="test@example.com",
        password="password",
        use_tls=True,
        from_addr="test@example.com",
        to_addrs=["admin@example.com"]
    )


@pytest.fixture
def wechat_config():
    """企业微信配置"""
    return WeChatWorkConfig(
        corp_id="test_corp_id",
        secret="test_secret",
        agent_id="test_agent_id",
        to_user="@all"
    )


@pytest.fixture
def dingtalk_config():
    """钉钉配置"""
    return DingTalkConfig(
        access_token="test_token",
        secret="test_secret"
    )


@pytest.fixture
def feishu_config():
    """飞书配置"""
    return FeishuConfig(
        app_id="test_app_id",
        app_secret="test_app_secret",
        webhook_url="test_webhook"
    )


@pytest.fixture
def sms_config():
    """短信配置"""
    return SMSConfig(
        api_url="https://sms.example.com/send",
        api_key="test_key",
        api_secret="test_secret",
        template_id="test_template",
        sign_name="test_sign",
        phone_numbers=["13800138000"]
    )


@pytest.mark.asyncio
async def test_email_alert_handler(test_alert, smtp_config):
    """测试邮件告警处理器"""
    handler = EmailAlertHandler(smtp_config)
    
    # Mock SMTP
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # 发送告警
        await handler.handle_alert(test_alert)
        
        # 验证SMTP调用
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            smtp_config.username,
            smtp_config.password
        )
        mock_server.send_message.assert_called_once()
        
        # 验证邮件内容
        sent_message = mock_server.send_message.call_args[0][0]
        assert sent_message["Subject"] == f"[{test_alert.level.name}] {test_alert.rule_name}"
        
        # 解码base64内容
        payload = sent_message.get_payload()[0]
        encoded_content = payload.get_payload()
        decoded_content = base64.b64decode(encoded_content).decode('utf-8')
        assert test_alert.message in decoded_content


@pytest.mark.asyncio
async def test_wechat_work_alert_handler(test_alert, wechat_config):
    """测试企业微信告警处理器"""
    handler = WeChatWorkAlertHandler(wechat_config)
    
    # Mock HTTP请求
    with patch("aiohttp.ClientSession.get") as mock_get, \
         patch("aiohttp.ClientSession.post") as mock_post:
        # Mock 获取token
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"errcode": 0, "access_token": "test_token"}
        )
        
        # Mock 发送消息
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"errcode": 0}
        )
        
        # 发送告警
        await handler.handle_alert(test_alert)
        
        # 验证API调用
        assert mock_get.call_count == 1
        assert mock_post.call_count == 1
        
        # 验证发送的消息
        sent_message = mock_post.call_args[1]["json"]["markdown"]["content"]
        assert test_alert.rule_name in sent_message
        assert test_alert.level.name in sent_message
        assert test_alert.message in sent_message
        assert test_alert.source in sent_message


@pytest.mark.asyncio
async def test_dingtalk_alert_handler(test_alert, dingtalk_config):
    """测试钉钉告警处理器"""
    handler = DingTalkAlertHandler(dingtalk_config)
    
    # Mock HTTP请求
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"errcode": 0}
        )
        
        # 发送告警
        await handler.handle_alert(test_alert)
        
        # 验证API调用
        assert mock_post.call_count == 1
        
        # 验证发送的消息
        sent_message = mock_post.call_args[1]["json"]["markdown"]["text"]
        assert test_alert.rule_name in sent_message
        assert test_alert.level.name in sent_message
        assert test_alert.message in sent_message
        assert test_alert.source in sent_message


@pytest.mark.asyncio
async def test_feishu_alert_handler(test_alert, feishu_config):
    """测试飞书告警处理器"""
    handler = FeishuAlertHandler(feishu_config)
    
    # Mock HTTP请求
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Mock 获取token和发送消息
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            side_effect=[
                {"code": 0, "tenant_access_token": "test_token", "expire": 7200},  # 获取token
                {"code": 0}  # 发送消息
            ]
        )
        
        # 发送告警
        await handler.handle_alert(test_alert)
        
        # 验证API调用
        assert mock_post.call_count == 2
        
        # 验证获取token的请求
        token_call = mock_post.call_args_list[0]
        assert token_call[1]["json"]["app_id"] == feishu_config.app_id
        assert token_call[1]["json"]["app_secret"] == feishu_config.app_secret
        
        # 验证发送消息的请求
        message_call = mock_post.call_args_list[1]
        sent_message = message_call[1]["json"]
        assert sent_message["msg_type"] == "interactive"
        assert test_alert.rule_name in sent_message["card"]["header"]["title"]["content"]
        assert test_alert.message in sent_message["card"]["elements"][0]["text"]["content"]


@pytest.mark.asyncio
async def test_sms_alert_handler(test_alert, sms_config):
    """测试短信告警处理器"""
    handler = SMSAlertHandler(sms_config)
    
    # Mock HTTP请求
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"code": 0}
        )
        
        # 发送告警
        await handler.handle_alert(test_alert)
        
        # 验证API调用
        assert mock_post.call_count == 1
        
        # 验证发送的消息
        sent_message = mock_post.call_args[1]["json"]
        assert sms_config.template_id in str(sent_message)
        assert sms_config.sign_name in str(sent_message)
        assert sms_config.phone_numbers[0] in str(sent_message)


@pytest.mark.asyncio
async def test_composite_alert_handler(test_alert):
    """测试组合告警处理器"""
    # 创建Mock处理器
    mock_handler1 = AsyncMock()
    mock_handler2 = AsyncMock()
    
    # 创建组合处理器
    handler = CompositeAlertHandler([mock_handler1, mock_handler2])
    
    # 发送告警
    await handler.handle_alert(test_alert)
    
    # 验证所有处理器都被调用
    mock_handler1.handle_alert.assert_called_once_with(test_alert)
    mock_handler2.handle_alert.assert_called_once_with(test_alert)


@pytest.mark.asyncio
async def test_handler_error_handling(test_alert, smtp_config):
    """测试错误处理"""
    handler = EmailAlertHandler(smtp_config)
    
    # Mock SMTP抛出异常
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("Test error")
        
        # 发送告警应该不会抛出异常
        await handler.handle_alert(test_alert)


def test_alert_level_colors():
    """测试告警级别颜色"""
    assert AlertLevel.INFO.get_color() == "#1E88E5"  # 蓝色
    assert AlertLevel.WARNING.get_color() == "#FFC107"  # 黄色
    assert AlertLevel.ERROR.get_color() == "#E53935"  # 红色
    assert AlertLevel.CRITICAL.get_color() == "#B71C1C"  # 深红色


def test_alert_message_truncation():
    """测试消息截断"""
    long_message = "x" * 1000
    alert = Alert(
        rule_name="test",
        level=AlertLevel.INFO,
        message=long_message,
        source="test",
        timestamp=datetime.now().timestamp(),
        events=[],
        context={}
    )
    
    # 验证消息被截断
    truncated_message = alert.get_truncated_message(100)
    assert len(truncated_message) <= 100
    assert truncated_message.endswith("...") 