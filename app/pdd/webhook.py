"""
拼多多 Webhook 消息处理器
处理拼多多开放平台推送的消息
"""
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import hashlib
import json
import logging
from typing import Dict, Any

from app.config import get_settings
from app.pdd.client import PddWebhookParser, CustomerMessage
from app.pdd.message_handler import MessageHandler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook/pdd", tags=["webhook"])


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    验证 Webhook 签名

    拼多多签名规则:
    1. 将 body + secret 拼接
    2. SHA256 加密
    3. 转为十六进制字符串
    """
    expected = hashlib.sha256(body + secret.encode()).hexdigest()
    return signature == expected


@router.post("/message")
async def handle_message(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    处理拼多多推送的消息

    拼多多会在以下情况推送消息:
    - 用户发送客服消息
    - 订单状态变更
    - 售后状态变更
    """
    settings = get_settings()
    body = await request.body()

    # 验证签名（如果配置了 secret）
    signature = request.headers.get("X-Pdd-Signature", "")
    # TODO: 实际部署时启用签名验证
    # if not verify_signature(body, signature, settings.pdd_client_secret):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    msg_type = data.get("type", "")

    # 根据消息类型分发处理
    if msg_type == "pdd_customer_service_message":
        # 客服消息
        message = PddWebhookParser.parse_message(data)
        if message:
            # 后台异步处理，立即返回 200
            background_tasks.add_task(MessageHandler.handle_customer_message, message)
        return JSONResponse({"code": 0, "msg": "success"})

    elif msg_type == "pdd_order_status_change":
        # 订单状态变更
        background_tasks.add_task(MessageHandler.handle_order_change, data)
        return JSONResponse({"code": 0, "msg": "success"})

    elif msg_type == "pdd_after_sale_status_change":
        # 售后状态变更
        background_tasks.add_task(MessageHandler.handle_after_sale_change, data)
        return JSONResponse({"code": 0, "msg": "success"})

    else:
        logger.warning(f"Unknown message type: {msg_type}")
        return JSONResponse({"code": 0, "msg": "ignored"})


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "pdd-webhook"}