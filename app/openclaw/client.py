"""
OpenClaw Fleet 客户端
连接 OpenClaw 协调中心，使用 AI 生成回复
"""
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    reply: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class OpenClawClient:
    """
    OpenClaw Fleet 客户端

    功能:
    - 提交任务到 Fleet 协调中心
    - 使用 AI 生成客服回复
    - 查询订单/物流信息（通过 AI 调用工具）
    """

    def __init__(
        self,
        fleet_url: str,
        instance_id: str,
        token: Optional[str] = None
    ):
        self.fleet_url = fleet_url.rstrip("/")
        self.instance_id = instance_id
        self.token = token
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._http_client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client:
            await self._http_client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Instance-Token"] = self.token
        return headers

    async def submit_task(
        self,
        task_type: str,
        message: str,
        context: Optional[Dict] = None,
        priority: int = 0
    ) -> str:
        """
        提交任务到 Fleet 协调中心

        Args:
            task_type: 任务类型 (customer_service_reply, order_query, etc.)
            message: 用户消息
            context: 上下文信息
            priority: 优先级 (0=普通, 1=高, 2=紧急)

        Returns:
            str: 任务ID
        """
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=60.0)

        try:
            response = await self._http_client.post(
                f"{self.fleet_url}/api/task/submit",
                headers=self._get_headers(),
                json={
                    "type": task_type,
                    "message": message,
                    "context": context or {},
                    "priority": priority,
                    "instance_id": self.instance_id
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("task_id", "")
        except httpx.HTTPError as e:
            logger.error(f"Failed to submit task: {e}")
            return ""

    async def get_task_result(self, task_id: str) -> TaskResult:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            TaskResult: 任务结果
        """
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=60.0)

        try:
            response = await self._http_client.get(
                f"{self.fleet_url}/api/task/{task_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "completed":
                return TaskResult(
                    success=True,
                    reply=result.get("result", {}).get("reply"),
                    metadata=result.get("result", {}).get("metadata")
                )
            elif result.get("status") == "failed":
                return TaskResult(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
            else:
                # 任务还在进行中
                return TaskResult(success=False, error="Task in progress")
        except httpx.HTTPError as e:
            logger.error(f"Failed to get task result: {e}")
            return TaskResult(success=False, error=str(e))

    async def generate_reply(
        self,
        message: str,
        intent: str,
        context: Optional[Dict] = None
    ) -> Optional[str]:
        """
        使用 AI 生成客服回复

        Args:
            message: 用户消息
            intent: 意图类型
            context: 上下文信息

        Returns:
            Optional[str]: AI 生成的回复，失败返回 None
        """
        # 构建提示词
        system_prompt = self._build_system_prompt(intent)
        user_prompt = self._build_user_prompt(message, context)

        try:
            # 提交任务
            task_id = await self.submit_task(
                task_type="customer_service_reply",
                message=user_prompt,
                context={
                    "system_prompt": system_prompt,
                    "intent": intent,
                    **(context or {})
                }
            )

            if not task_id:
                logger.warning("Failed to submit task to OpenClaw")
                return None

            # 等待结果（简化版，实际应该用 WebSocket 或轮询）
            # 这里假设 OpenClaw 会直接返回结果
            result = await self.get_task_result(task_id)

            if result.success:
                return result.reply
            else:
                logger.warning(f"OpenClaw task failed: {result.error}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate reply via OpenClaw: {e}")
            return None

    def _build_system_prompt(self, intent: str) -> str:
        """构建系统提示词"""
        base_prompt = """你是一个专业的拼多多电商客服助手。你的职责是：
1. 友好、专业地回答用户问题
2. 准确查询订单和物流信息
3. 处理售后问题
4. 对于无法处理的问题，引导用户转人工客服

回复要求：
- 简洁明了，避免冗长
- 使用礼貌用语
- 如需查询订单，请引导用户提供订单号
- 对于投诉、退款等敏感问题，建议转人工"""

        intent_prompts = {
            "order_query": "\n\n当前用户正在查询订单，请帮助用户了解订单状态。",
            "logistics_query": "\n\n当前用户正在查询物流，请帮助用户了解快递状态。",
            "product_query": "\n\n当前用户正在咨询商品信息，请准确回答商品相关问题。",
            "after_sale": "\n\n当前用户有售后问题，请耐心解答并建议解决方案。如问题复杂，建议转人工。",
            "complaint": "\n\n当前用户正在投诉，请诚恳道歉并建议转人工客服处理。",
        }

        return base_prompt + intent_prompts.get(intent, "")

    def _build_user_prompt(self, message: str, context: Optional[Dict]) -> str:
        """构建用户提示词"""
        prompt = f"用户消息：{message}"

        if context:
            if context.get("order_info"):
                order = context["order_info"]
                prompt += f"\n\n订单信息：{json.dumps(order, ensure_ascii=False)}"
            if context.get("history"):
                prompt += f"\n\n历史消息：{json.dumps(context['history'], ensure_ascii=False)}"

        return prompt

    async def health_check(self) -> bool:
        """健康检查"""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=10.0)

        try:
            response = await self._http_client.get(
                f"{self.fleet_url}/api/health",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False


class MockOpenClawClient(OpenClawClient):
    """
    Mock 客户端，用于测试
    不需要真实的 OpenClaw 服务
    """

    async def generate_reply(
        self,
        message: str,
        intent: str,
        context: Optional[Dict] = None
    ) -> Optional[str]:
        """Mock 生成回复"""
        # 简单的规则回复
        replies = {
            "order_query": "您好，请提供您的订单号，我帮您查询订单状态。",
            "logistics_query": "您好，请提供您的订单号，我帮您查询物流信息。",
            "product_query": "您好，请问您想了解哪款商品的信息？",
            "after_sale": "您好，售后问题需要人工处理，正在为您转接人工客服，请稍候...",
            "complaint": "非常抱歉给您带来不好的体验，正在为您转接人工客服处理，请稍候...",
            "general": "您好，请问有什么可以帮您的？"
        }
        return replies.get(intent, replies["general"])

    async def health_check(self) -> bool:
        return True