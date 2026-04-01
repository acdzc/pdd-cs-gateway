"""
消息处理器核心逻辑
处理客服消息、订单变更、售后变更
"""
import re
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json

from app.config import get_settings
from app.pdd.client import PddClient, CustomerMessage, MessageType, ReplyResult
from app.feishu.bot import FeishuNotifier
from app.openclaw.client import OpenClawClient

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型"""
    ORDER_QUERY = "order_query"           # 订单查询
    LOGISTICS_QUERY = "logistics_query"   # 物流查询
    PRODUCT_QUERY = "product_query"       # 商品咨询
    AFTER_SALE = "after_sale"             # 售后问题
    COMPLAINT = "complaint"               # 投诉
    GENERAL = "general"                   # 一般咨询
    UNKNOWN = "unknown"                   # 未知


@dataclass
class MessageContext:
    """消息上下文"""
    session_id: str
    user_id: str
    history: list
    order_info: Optional[Dict] = None
    goods_info: Optional[Dict] = None


class IntentClassifier:
    """意图分类器"""

    # 关键词规则
    PATTERNS = {
        IntentType.ORDER_QUERY: [
            r"订单", r"下单", r"买了", r"拍了", r"订单号", r"订单状态",
            r"什么时候发货", r"发货了吗", r"我的单子"
        ],
        IntentType.LOGISTICS_QUERY: [
            r"物流", r"快递", r"快递单号", r"到哪了", r"什么时候到",
            r"配送", r"签收", r"运输中"
        ],
        IntentType.PRODUCT_QUERY: [
            r"有货吗", r"库存", r"尺寸", r"颜色", r"规格", r"材质",
            r"多少钱", r"价格", r"优惠", r"活动"
        ],
        IntentType.AFTER_SALE: [
            r"退货", r"退款", r"换货", r"质量", r"坏了", r"破损",
            r"不满意", r"有问题"
        ],
        IntentType.COMPLAINT: [
            r"投诉", r"举报", r"差评", r"维权", r"起诉", r"骗子"
        ],
    }

    # 人工接管关键词
    HUMAN_KEYWORDS = ["人工", "转人工", "客服", "真人"]

    @classmethod
    def classify(cls, text: str) -> IntentType:
        """分类意图"""
        text = text.lower()

        # 检查人工接管
        for kw in cls.HUMAN_KEYWORDS:
            if kw in text:
                return IntentType.COMPLAINT  # 转人工处理

        # 规则匹配
        for intent, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return intent

        return IntentType.GENERAL

    @classmethod
    def need_human_takeover(cls, text: str, keywords: list) -> bool:
        """判断是否需要人工接管"""
        text = text.lower()
        for kw in keywords:
            if kw in text:
                return True
        return False


class ReplyGenerator:
    """回复生成器"""

    # 模板回复
    TEMPLATES = {
        IntentType.ORDER_QUERY: {
            "default": "您好，请提供您的订单号，我帮您查询订单状态。",
            "with_order": "您的订单 {order_sn} 当前状态：{status}，预计 {estimated_time} 发货。"
        },
        IntentType.LOGISTICS_QUERY: {
            "default": "您好，请提供您的订单号，我帮您查询物流信息。",
            "with_logistics": "您的快递 {express_company}（单号：{express_no}）当前状态：{status}。"
        },
        IntentType.PRODUCT_QUERY: {
            "default": "您好，请问您想了解哪款商品的信息？",
        },
        IntentType.AFTER_SALE: {
            "default": "您好，售后问题需要人工处理，正在为您转接人工客服，请稍候...",
        },
        IntentType.COMPLAINT: {
            "default": "非常抱歉给您带来不好的体验，正在为您转接人工客服处理，请稍候...",
        },
        IntentType.GENERAL: {
            "default": "您好，请问有什么可以帮您的？",
        }
    }

    @classmethod
    def generate(cls, intent: IntentType, context: MessageContext) -> str:
        """生成回复"""
        templates = cls.TEMPLATES.get(intent, cls.TEMPLATES[IntentType.GENERAL])

        if intent == IntentType.ORDER_QUERY and context.order_info:
            return templates["with_order"].format(
                order_sn=context.order_info.get("order_sn", ""),
                status=context.order_info.get("order_status_desc", "未知"),
                estimated_time="尽快"
            )
        elif intent == IntentType.LOGISTICS_QUERY and context.order_info:
            logistics = context.order_info.get("logistics", {})
            return templates["with_logistics"].format(
                express_company=logistics.get("express_company", "快递"),
                express_no=logistics.get("tracking_number", ""),
                status=logistics.get("status_desc", "运输中")
            )

        return templates.get("default", templates.get("default", "您好，请问有什么可以帮您的？"))


class MessageHandler:
    """消息处理器"""

    _pdd_client: Optional[PddClient] = None
    _feishu: Optional[FeishuNotifier] = None
    _openclaw: Optional[OpenClawClient] = None

    @classmethod
    def _get_clients(cls):
        """懒加载客户端"""
        if cls._pdd_client is None:
            settings = get_settings()
            cls._pdd_client = PddClient(
                client_id=settings.pdd_client_id,
                client_secret=settings.pdd_client_secret,
                access_token=settings.pdd_access_token
            )
            cls._feishu = FeishuNotifier(
                app_id=settings.feishu_app_id,
                app_secret=settings.feishu_app_secret
            )
            cls._openclaw = OpenClawClient(
                fleet_url=settings.fleet_url,
                instance_id=settings.instance_id,
                token=settings.fleet_token
            )
        return cls._pdd_client, cls._feishu, cls._openclaw

    @classmethod
    async def handle_customer_message(cls, message: CustomerMessage):
        """
        处理客服消息

        流程:
        1. 意图分类
        2. 判断是否需要人工接管
        3. 自动回复 或 转人工
        """
        pdd_client, feishu, openclaw = cls._get_clients()
        settings = get_settings()

        logger.info(f"Processing message from {message.from_uid}: {message.content}")

        # 只处理文本消息
        if message.msg_type != MessageType.TEXT:
            return

        text = message.content

        # 1. 检查人工接管关键词
        if IntentClassifier.need_human_takeover(text, settings.human_takeover_keywords):
            await cls._handle_human_takeover(message, feishu, "用户请求人工服务")
            return

        # 2. 意图分类
        intent = IntentClassifier.classify(text)
        logger.info(f"Classified intent: {intent}")

        # 3. 构建上下文
        context = MessageContext(
            session_id=message.session_id,
            user_id=message.from_uid,
            history=[]
        )

        # 4. 查询相关信息
        if intent in [IntentType.ORDER_QUERY, IntentType.LOGISTICS_QUERY]:
            # 尝试从消息中提取订单号
            order_sn = cls._extract_order_sn(text)
            if order_sn:
                context.order_info = await pdd_client.get_order_info(order_sn)

        # 5. 生成回复
        if settings.auto_reply_enabled:
            # 尝试使用 OpenClaw AI 生成回复
            ai_reply = await openclaw.generate_reply(
                message=text,
                intent=intent.value,
                context={
                    "session_id": message.session_id,
                    "user_id": message.from_uid,
                    "order_info": context.order_info
                }
            )

            if ai_reply:
                reply_content = ai_reply
            else:
                # 降级到模板回复
                reply_content = ReplyGenerator.generate(intent, context)

            # 6. 发送回复
            async with pdd_client:
                result = await pdd_client.send_message(
                    session_id=message.session_id,
                    content=reply_content
                )

            if result.success:
                logger.info(f"Reply sent: {reply_content[:50]}...")
            else:
                logger.error(f"Failed to send reply: {result.error_msg}")

    @classmethod
    async def handle_order_change(cls, data: Dict):
        """处理订单状态变更"""
        logger.info(f"Order status changed: {data}")
        # 可以发送飞书通知
        pdd_client, feishu, openclaw = cls._get_clients()
        # TODO: 实现订单变更通知

    @classmethod
    async def handle_after_sale_change(cls, data: Dict):
        """处理售后状态变更"""
        logger.info(f"After-sale status changed: {data}")
        pdd_client, feishu, openclaw = cls._get_clients()
        # TODO: 实现售后变更通知

    @classmethod
    async def _handle_human_takeover(
        cls,
        message: CustomerMessage,
        feishu: FeishuNotifier,
        reason: str
    ):
        """处理人工接管"""
        logger.info(f"Human takeover: {reason}")

        # 发送飞书通知
        await feishu.notify_human_takeover(
            session_id=message.session_id,
            user_msg=message.content,
            reason=reason
        )

    @staticmethod
    def _extract_order_sn(text: str) -> Optional[str]:
        """从文本中提取订单号"""
        # 拼多多订单号通常是 18-20 位数字
        match = re.search(r'\d{18,20}', text)
        return match.group(0) if match else None