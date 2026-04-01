# Models
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class WebhookMessage(BaseModel):
    """Webhook 消息模型"""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[int] = None


class CustomerServiceMessage(BaseModel):
    """客服消息模型"""
    msg_id: str
    session_id: str
    content: str
    msg_type: int = 1  # 1=文本, 2=图片, 3=商品卡片
    from_uid: str
    from_role: str
    to_uid: str
    to_role: str
    timestamp: int
    nickname: Optional[str] = None


class ReplyRequest(BaseModel):
    """回复请求模型"""
    session_id: str
    content: str
    msg_type: int = 1


class ReplyResponse(BaseModel):
    """回复响应模型"""
    success: bool
    msg_id: Optional[str] = None
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    user_id: str
    user_nickname: Optional[str] = None
    status: int = 1  # 1=等待, 2=处理中, 3=已关闭
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    message_count: int = 0
    auto_reply_count: int = 0


class OrderInfo(BaseModel):
    """订单信息模型"""
    order_sn: str
    order_status: int
    order_status_desc: str
    goods_id: Optional[str] = None
    goods_name: Optional[str] = None
    goods_price: Optional[float] = None
    goods_quantity: Optional[int] = None
    create_time: Optional[datetime] = None
    pay_time: Optional[datetime] = None
    ship_time: Optional[datetime] = None
    logistics_company: Optional[str] = None
    tracking_number: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    components: Dict[str, bool]