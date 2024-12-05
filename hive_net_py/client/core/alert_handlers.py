"""
HiveNet 告警处理器模块
"""
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import asdict
import time

from .event_monitor import Alert, AlertHandler, AlertLevel

logger = logging.getLogger(__name__)

class SMTPConfig:
    """SMTP配置"""
    def __init__(self,
                 host: str,
                 port: int = 25,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 use_tls: bool = False,
                 from_addr: str = "alert@example.com",
                 to_addrs: List[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_addr = from_addr
        self.to_addrs = to_addrs or []

class EmailAlertHandler(AlertHandler):
    """邮件告警处理器"""
    
    def __init__(self, config: SMTPConfig):
        self.config = config
    
    async def handle_alert(self, alert: Alert):
        """发送告警邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config.from_addr
            msg['To'] = ', '.join(self.config.to_addrs)
            msg['Subject'] = f"[{alert.level.name}] {alert.rule_name}"
            
            # 构建邮件内容
            body = (
                f"告警信息:\n"
                f"规则: {alert.rule_name}\n"
                f"级别: {alert.level.name}\n"
                f"来源: {alert.source}\n"
                f"时间: {alert.timestamp}\n"
                f"消息: {alert.message}\n"
                f"相关事件数: {len(alert.events)}\n"
            )
            msg.attach(MIMEText(body, 'plain'))
            
            # 异步发送邮件
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_email,
                msg
            )
            
            logger.info(f"告警邮件已发送: {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"发送告警邮件失败: {e}")
    
    def _send_email(self, msg: MIMEMultipart):
        """同步发送邮件"""
        with smtplib.SMTP(self.config.host, self.config.port) as server:
            if self.config.use_tls:
                server.starttls()
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            server.send_message(msg)

class WeChatWorkConfig:
    """企业微信配置"""
    def __init__(self,
                 corp_id: str,
                 agent_id: str,
                 secret: str,
                 to_user: Optional[str] = None,
                 to_party: Optional[str] = None,
                 to_tag: Optional[str] = None):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.to_user = to_user
        self.to_party = to_party
        self.to_tag = to_tag
        self._access_token = None
        self._token_expires = 0

class WeChatWorkAlertHandler(AlertHandler):
    """企业微信告警处理器"""
    
    def __init__(self, config: WeChatWorkConfig):
        self.config = config
        self._token_lock = asyncio.Lock()
    
    async def handle_alert(self, alert: Alert):
        """发送企业微信告警"""
        try:
            # 获取访问令牌
            async with self._token_lock:
                access_token = await self._get_access_token()
            
            if not access_token:
                logger.error("获取企业微信访问令牌失败")
                return
            
            # 构建消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": (
                        f"### [{alert.level.name}] {alert.rule_name}\n"
                        f"> 来源: {alert.source}\n"
                        f"> 时间: {alert.timestamp}\n"
                        f"> 消息: {alert.message}\n"
                        f"> 相关事件数: {len(alert.events)}"
                    )
                },
                "touser": self.config.to_user or "@all",
                "toparty": self.config.to_party,
                "totag": self.config.to_tag,
                "agentid": self.config.agent_id,
                "safe": 0
            }
            
            # 发送消息
            async with aiohttp.ClientSession() as session:
                url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
                async with session.post(url, json=message) as response:
                    result = await response.json()
                    if result.get("errcode") != 0:
                        logger.error(f"发送企业微信告警失败: {result}")
                    else:
                        logger.info(f"企业微信告警已发送: {alert.rule_name}")
                        
        except Exception as e:
            logger.error(f"发送企业微信告警失败: {e}")
    
    async def _get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        try:
            async with aiohttp.ClientSession() as session:
                url = (
                    "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
                    f"?corpid={self.config.corp_id}"
                    f"&corpsecret={self.config.secret}"
                )
                async with session.get(url) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return result.get("access_token")
            return None
        except Exception as e:
            logger.error(f"获取企业微信访问令牌失败: {e}")
            return None

class DingTalkConfig:
    """钉钉配置"""
    def __init__(self,
                 access_token: str,
                 secret: Optional[str] = None,
                 at_mobiles: List[str] = None,
                 at_all: bool = False):
        self.access_token = access_token
        self.secret = secret
        self.at_mobiles = at_mobiles or []
        self.at_all = at_all

class DingTalkAlertHandler(AlertHandler):
    """钉钉告警处理器"""
    
    def __init__(self, config: DingTalkConfig):
        self.config = config
    
    async def handle_alert(self, alert: Alert):
        """发送钉钉告警"""
        try:
            # 构建消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"[{alert.level.name}] {alert.rule_name}",
                    "text": (
                        f"### [{alert.level.name}] {alert.rule_name}\n"
                        f"> 来源: {alert.source}\n"
                        f"> 时间: {alert.timestamp}\n"
                        f"> 消息: {alert.message}\n"
                        f"> 相关事件数: {len(alert.events)}\n"
                    )
                },
                "at": {
                    "atMobiles": self.config.at_mobiles,
                    "isAtAll": self.config.at_all
                }
            }
            
            # 发送消息
            async with aiohttp.ClientSession() as session:
                url = f"https://oapi.dingtalk.com/robot/send?access_token={self.config.access_token}"
                async with session.post(url, json=message) as response:
                    result = await response.json()
                    if result.get("errcode") != 0:
                        logger.error(f"发送钉钉告警失败: {result}")
                    else:
                        logger.info(f"钉钉告警已发送: {alert.rule_name}")
                        
        except Exception as e:
            logger.error(f"发送钉钉���警失败: {e}")

class FeishuConfig:
    """飞书配置"""
    def __init__(self,
                 app_id: str,
                 app_secret: str,
                 webhook_url: Optional[str] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.webhook_url = webhook_url

class FeishuAlertHandler(AlertHandler):
    """飞书告警处理器"""
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self._token_lock = asyncio.Lock()
        self._access_token = None
        self._token_expires = 0
    
    async def handle_alert(self, alert: Alert):
        """发送飞书告警"""
        try:
            # 获取访问令牌
            async with self._token_lock:
                access_token = await self._get_access_token()
            
            if not access_token:
                logger.error("获取飞书访问令牌失败")
                return
            
            # 构建消息
            message = {
                "msg_type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"[{alert.level.name}] {alert.rule_name}"
                        },
                        "template": self._get_alert_color(alert.level)
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": (
                                    f"**来源:** {alert.source}\n"
                                    f"**时间:** {alert.timestamp}\n"
                                    f"**消息:** {alert.message}\n"
                                    f"**相关事件数:** {len(alert.events)}"
                                )
                            }
                        }
                    ]
                }
            }
            
            # 发送消息
            async with aiohttp.ClientSession() as session:
                if self.config.webhook_url:
                    # 使用 Webhook 发送
                    url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{self.config.webhook_url}"
                    async with session.post(url, json=message) as response:
                        result = await response.json()
                        if result.get("code") != 0:
                            logger.error(f"发送飞书告警失败: {result}")
                        else:
                            logger.info(f"飞书告警已发送: {alert.rule_name}")
                else:
                    # 使用应用发送
                    url = f"https://open.feishu.cn/open-apis/message/v4/send"
                    headers = {"Authorization": f"Bearer {access_token}"}
                    async with session.post(url, headers=headers, json=message) as response:
                        result = await response.json()
                        if result.get("code") != 0:
                            logger.error(f"发送飞书告警失败: {result}")
                        else:
                            logger.info(f"飞书告警已发送: {alert.rule_name}")
                        
        except Exception as e:
            logger.error(f"发送飞书告警失败: {e}")
    
    async def _get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        current_time = time.time()
        
        # 检查缓存的令牌是否有效
        if self._access_token and current_time < self._token_expires:
            return self._access_token
        
        try:
            # 获取新令牌
            async with aiohttp.ClientSession() as session:
                url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
                data = {
                    "app_id": self.config.app_id,
                    "app_secret": self.config.app_secret
                }
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("code") == 0:
                        self._access_token = result.get("tenant_access_token")
                        self._token_expires = current_time + result.get("expire", 7200)
                        return self._access_token
            
            return None
            
        except Exception as e:
            logger.error(f"获取飞书访问令牌失败: {e}")
            return None
    
    def _get_alert_color(self, level: AlertLevel) -> str:
        """获取告警颜色"""
        return {
            AlertLevel.INFO: "blue",
            AlertLevel.WARNING: "yellow",
            AlertLevel.ERROR: "red",
            AlertLevel.CRITICAL: "purple"
        }.get(level, "grey")

class SMSConfig:
    """短信配置"""
    def __init__(self,
                 api_url: str,
                 api_key: str,
                 api_secret: str,
                 template_id: str,
                 sign_name: str,
                 phone_numbers: List[str]):
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.template_id = template_id
        self.sign_name = sign_name
        self.phone_numbers = phone_numbers

class SMSAlertHandler(AlertHandler):
    """短信告警处理器"""
    
    def __init__(self, config: SMSConfig):
        self.config = config
    
    async def handle_alert(self, alert: Alert):
        """发送短信告警"""
        try:
            # 构建短信参数
            template_param = {
                "level": alert.level.name,
                "rule": alert.rule_name,
                "source": alert.source,
                "message": alert.message[:50]  # 限制长度
            }
            
            # 为每个手机号发送短信
            for phone in self.config.phone_numbers:
                try:
                    await self._send_sms(phone, template_param)
                except Exception as e:
                    logger.error(f"发送短信到 {phone} 失败: {e}")
            
            logger.info(f"短信告警已发送: {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"发送短信告警失败: {e}")
    
    async def _send_sms(self, phone: str, template_param: Dict[str, str]):
        """发送单条短信"""
        params = {
            "PhoneNumbers": phone,
            "SignName": self.config.sign_name,
            "TemplateCode": self.config.template_id,
            "TemplateParam": json.dumps(template_param)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.config.api_url,
                                  headers={"Authorization": self._get_auth_header()},
                                  json=params) as response:
                result = await response.json()
                if not result.get("success", False):
                    raise Exception(f"SMS API error: {result}")
    
    def _get_auth_header(self) -> str:
        """获取认证头"""
        # 实现具体的认证逻辑
        return f"Bearer {self.config.api_key}"

class CompositeAlertHandler(AlertHandler):
    """组合告警处理器"""
    
    def __init__(self, handlers: List[AlertHandler] = None):
        self.handlers = handlers or []
    
    def add_handler(self, handler: AlertHandler):
        """添加处理器"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: AlertHandler):
        """移除处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    async def handle_alert(self, alert: Alert):
        """处理告警"""
        tasks = []
        for handler in self.handlers:
            try:
                task = asyncio.create_task(handler.handle_alert(alert))
                tasks.append(task)
            except Exception as e:
                logger.error(f"创建告警处理任务失败: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True) 