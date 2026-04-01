"""
飞书消息通知
使用飞书机器人发送客服相关通知
"""
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str
    app_secret: str
    webhook_url: Optional[str] = None
    receive_id: Optional[str] = None


class FeishuNotifier:
    """
    飞书消息通知器

    功能:
    - 发送人工接管通知
    - 发送订单异常通知
    - 发送系统告警
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        webhook_url: Optional[str] = None,
        receive_id: Optional[str] = None
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.webhook_url = webhook_url
        self.receive_id = receive_id
        self._tenant_access_token: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_access_token:
            return self._tenant_access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            result = response.json()
            if result.get("code") == 0:
                self._tenant_access_token = result.get("tenant_access_token")
                return self._tenant_access_token
            else:
                logger.error(f"Failed to get tenant_access_token: {result}")
                raise Exception(f"Feishu auth failed: {result.get('msg')}")

    async def send_message(
        self,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: Dict[str, Any]
    ) -> bool:
        """
        发送飞书消息

        Args:
            receive_id_type: 接收者类型 (open_id, user_id, union_id, email, chat_id)
            receive_id: 接收者ID
            msg_type: 消息类型 (text, post, image, etc.)
            content: 消息内容

        Returns:
            bool: 是否发送成功
        """
        token = await self._get_tenant_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/im/v1/messages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                params={"receive_id_type": receive_id_type},
                json={
                    "receive_id": receive_id,
                    "msg_type": msg_type,
                    "content": json.dumps(content)
                }
            )
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"Message sent to {receive_id}")
                return True
            else:
                logger.error(f"Failed to send message: {result}")
                return False

    async def send_text(self, receive_id: str, text: str) -> bool:
        """发送文本消息"""
        return await self.send_message(
            receive_id_type="chat_id",
            receive_id=receive_id,
            msg_type="text",
            content={"text": text}
        )

    async def send_card(
        self,
        receive_id: str,
        title: str,
        content: str,
        color: str = "blue"
    ) -> bool:
        """
        发送消息卡片

        Args:
            receive_id: 接收者ID
            title: 卡片标题
            content: 卡片内容 (Markdown)
            color: 卡片颜色 (blue, red, green, yellow)
        """
        card = {
            "type": "template",
            "data": {
                "template_id": "AAqkz9PpJz",  # 可以使用自定义模板
                "template_variable": {
                    "title": title,
                    "content": content,
                    "color": color
                }
            }
        }

        # 简单卡片结构
        card_simple = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                }
            ]
        }

        return await self.send_message(
            receive_id_type="chat_id",
            receive_id=receive_id,
            msg_type="interactive",
            content=card_simple
        )

    async def notify_human_takeover(
        self,
        session_id: str,
        user_msg: str,
        reason: str
    ) -> bool:
        """
        发送人工接管通知

        Args:
            session_id: 拼多多会话ID
            user_msg: 用户消息
            reason: 接管原因
        """
        if not self.receive_id:
            logger.warning("No receive_id configured for Feishu")
            return False

        content = f"""**接管原因**: {reason}

**用户消息**: {user_msg}

**会话ID**: `{session_id}`

**操作**: [查看会话](https://mms.pinduoduo.com/chat)"""

        return await self.send_card(
            receive_id=self.receive_id,
            title="⚠️ 需人工介入",
            content=content,
            color="red"
        )

    async def send_webhook_message(self, title: str, content: str) -> bool:
        """
        通过 Webhook 发送消息（无需 tenant_access_token）

        适用于自定义机器人
        """
        if not self.webhook_url:
            logger.warning("No webhook_url configured")
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json={
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {"tag": "plain_text", "content": title},
                            "template": "blue"
                        },
                        "elements": [
                            {"tag": "markdown", "content": content}
                        ]
                    }
                }
            )
            result = response.json()
            return result.get("StatusCode") == 0


class FeishuCardBuilder:
    """飞书消息卡片构建器"""

    @staticmethod
    def build_customer_service_card(
        session_id: str,
        user_name: str,
        user_msg: str,
        intent: str,
        auto_reply: str,
        need_human: bool = False
    ) -> Dict:
        """构建客服消息卡片"""
        color = "red" if need_human else "blue"
        title = "⚠️ 需人工介入" if need_human else "💬 客服消息"

        elements = [
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**用户**: {user_name}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**意图**: {intent}"}}
                ]
            },
            {"tag": "hr"},
            {"tag": "markdown", "content": f"**用户消息**:\n{user_msg}"},
            {"tag": "hr"},
            {"tag": "markdown", "content": f"**自动回复**:\n{auto_reply}"},
            {"tag": "hr"},
            {"tag": "action", "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看会话"},
                    "url": f"https://mms.pinduoduo.com/chat?session={session_id}",
                    "type": "primary"
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "接管会话"},
                    "type": "default"
                }
            ]}
        ]

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": elements
        }