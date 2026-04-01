"""
拼多多开放平台 API 客户端
文档: https://open.pinduoduo.com/application/document/browse?idStr=API_LIST
"""
import hashlib
import time
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    TEXT = 1      # 文本
    IMAGE = 2     # 图片
    GOODS = 3     # 商品卡片
    ORDER = 4     # 订单卡片


class SessionStatus(Enum):
    """会话状态"""
    WAITING = 1   # 等待处理
    PROCESSING = 2  # 处理中
    CLOSED = 3    # 已关闭


@dataclass
class CustomerMessage:
    """客服消息"""
    msg_id: str
    session_id: str
    content: str
    msg_type: MessageType
    from_uid: str
    from_role: str
    to_uid: str
    to_role: str
    timestamp: int
    nickname: Optional[str] = None
    goods_id: Optional[str] = None
    order_sn: Optional[str] = None


@dataclass
class ReplyResult:
    """回复结果"""
    success: bool
    msg_id: Optional[str] = None
    error_msg: Optional[str] = None


class PddClient:
    """
    拼多多开放平台 API 客户端

    使用方式:
        client = PddClient(client_id, client_secret)
        client.access_token = "your_access_token"  # 从授权获取

        # 发送消息
        result = await client.send_message(session_id, "您好，有什么可以帮您？")

        # 获取会话列表
        sessions = await client.get_session_list()
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_url: str = "https://api-gw.pinduoduo.com/api/router",
        access_token: Optional[str] = None,
        proxy: Optional[str] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_url = api_url
        self.access_token = access_token
        self.proxy = proxy  # None = 不使用代理
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        # trust_env=False 禁用系统代理，避免 SOCKS 代理依赖问题
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            proxy=self.proxy,
            trust_env=False if self.proxy is None else True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()

    def _sign(self, params: Dict[str, Any]) -> str:
        """
        生成 API 签名

        签名规则:
        1. 将所有参数按 key 字典序排序
        2. 拼接: secret + key1value1key2value2... + secret
        3. MD5 加密并转大写
        """
        # 过滤空值
        params = {k: v for k, v in params.items() if v is not None}
        sorted_params = sorted(params.items())
        sign_str = self.client_secret + "".join(f"{k}{v}" for k, v in sorted_params) + self.client_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    def _build_params(self, method: str, **kwargs) -> Dict[str, Any]:
        """构建请求参数"""
        params = {
            "type": method,
            "client_id": self.client_id,
            "timestamp": int(time.time()),
            "data_type": "JSON",
            **kwargs
        }
        if self.access_token:
            params["access_token"] = self.access_token
        params["sign"] = self._sign(params)
        return params

    async def _request(self, method: str, **kwargs) -> Dict[str, Any]:
        """发送 API 请求"""
        params = self._build_params(method, **kwargs)

        if not self._http_client:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                proxy=self.proxy,
                trust_env=False if self.proxy is None else True
            )

        try:
            response = await self._http_client.post(self.api_url, data=params)
            response.raise_for_status()
            result = response.json()

            # 检查业务错误
            if "error_response" in result:
                error = result["error_response"]
                logger.error(f"PDD API error: {error}")
                return {"success": False, "error": error}

            return result
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return {"success": False, "error": str(e)}

    # ============ 客服消息 API ============

    async def send_message(
        self,
        session_id: str,
        content: str,
        msg_type: MessageType = MessageType.TEXT,
        **extra
    ) -> ReplyResult:
        """
        发送客服消息

        Args:
            session_id: 会话ID
            content: 消息内容（文本/图片URL/商品ID等）
            msg_type: 消息类型
            extra: 额外参数（如商品卡片需要的商品信息）

        Returns:
            ReplyResult: 发送结果
        """
        result = await self._request(
            "pdd.customer.service.message.send",
            session_id=session_id,
            content=content,
            msg_type=msg_type.value,
            **extra
        )

        if result.get("success") is False:
            error = result.get("error")
            if isinstance(error, dict):
                error_msg = error.get("error_msg", str(error))
            else:
                error_msg = str(error) if error else "Unknown error"
            return ReplyResult(success=False, error_msg=error_msg)

        response = result.get("pdd_customer_service_message_send_response", {})
        return ReplyResult(
            success=True,
            msg_id=response.get("msg_id")
        )

    async def get_session_list(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[SessionStatus] = None
    ) -> List[Dict]:
        """
        获取会话列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 会话状态过滤
        """
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status.value

        result = await self._request("pdd.customer.service.session.get", **params)

        if result.get("success") is False:
            return []

        response = result.get("pdd_customer_service_session_get_response", {})
        return response.get("session_list", [])

    async def get_history(
        self,
        session_id: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[Dict]:
        """
        获取聊天记录

        Args:
            session_id: 会话ID
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            page: 页码
            page_size: 每页数量
        """
        params = {
            "session_id": session_id,
            "page": page,
            "page_size": page_size
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        result = await self._request("pdd.customer.service.history.get", **params)

        if result.get("success") is False:
            return []

        response = result.get("pdd_customer_service_history_get_response", {})
        return response.get("message_list", [])

    # ============ 订单 API ============

    async def get_order_info(self, order_sn: str) -> Optional[Dict]:
        """
        获取订单详情

        Args:
            order_sn: 订单号
        """
        result = await self._request("pdd.order.info.get", order_sn=order_sn)

        if result.get("success") is False:
            return None

        return result.get("order_info_get_response", {})

    async def get_logistics(self, order_sn: str) -> Optional[Dict]:
        """
        获取物流轨迹

        Args:
            order_sn: 订单号
        """
        result = await self._request("pdd.logistics.tracking.get", order_sn=order_sn)

        if result.get("success") is False:
            return None

        return result.get("logistics_tracking_get_response", {})

    async def get_order_list(
        self,
        start_updated_time: int,
        end_updated_time: int,
        order_status: Optional[int] = None,
        page: int = 1,
        page_size: int = 100
    ) -> List[Dict]:
        """
        获取订单列表

        Args:
            start_updated_time: 开始更新时间戳（秒）
            end_updated_time: 结束更新时间戳（秒）
            order_status: 订单状态
            page: 页码
            page_size: 每页数量
        """
        params = {
            "start_updated_time": start_updated_time,
            "end_updated_time": end_updated_time,
            "page": page,
            "page_size": page_size
        }
        if order_status:
            params["order_status"] = order_status

        result = await self._request("pdd.order.list.get", **params)

        if result.get("success") is False:
            return []

        response = result.get("order_list_get_response", {})
        return response.get("order_list", [])


class PddWebhookParser:
    """拼多多 Webhook 消息解析器"""

    @staticmethod
    def parse_message(data: Dict) -> Optional[CustomerMessage]:
        """解析客服消息"""
        try:
            msg_data = data.get("data", {})
            return CustomerMessage(
                msg_id=msg_data.get("msg_id"),
                session_id=msg_data.get("session_id"),
                content=msg_data.get("content"),
                msg_type=MessageType(msg_data.get("msg_type", 1)),
                from_uid=msg_data.get("from", {}).get("uid"),
                from_role=msg_data.get("from", {}).get("role"),
                to_uid=msg_data.get("to", {}).get("uid"),
                to_role=msg_data.get("to", {}).get("role"),
                timestamp=msg_data.get("timestamp"),
                nickname=msg_data.get("nickname"),
                goods_id=msg_data.get("goods_id"),
                order_sn=msg_data.get("order_sn")
            )
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None