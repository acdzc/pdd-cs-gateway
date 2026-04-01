"""
拼多多客服网关 - 配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "pdd-cs-gateway"
    app_version: str = "1.0.0"
    debug: bool = False

    # 拼多多开放平台配置
    pdd_client_id: str = Field(default="", alias="PDD_CLIENT_ID")
    pdd_client_secret: str = Field(default="", alias="PDD_CLIENT_SECRET")
    pdd_access_token: Optional[str] = Field(default=None, alias="PDD_ACCESS_TOKEN")
    pdd_api_url: str = "https://api-gw.pinduoduo.com/api/router"

    # 飞书配置
    feishu_app_id: str = Field(default="", alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", alias="FEISHU_APP_SECRET")
    feishu_webhook_url: Optional[str] = Field(default=None, alias="FEISHU_WEBHOOK_URL")
    feishu_receive_id: Optional[str] = Field(default=None, alias="FEISHU_RECEIVE_ID")  # 接收消息的用户/群ID

    # OpenClaw Fleet 配置
    fleet_url: str = Field(default="http://localhost:18789", alias="FLEET_URL")
    fleet_token: Optional[str] = Field(default=None, alias="FLEET_TOKEN")
    instance_id: str = "pdd-cs-gateway-001"

    # Redis 配置
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # 自动回复配置
    auto_reply_enabled: bool = True
    human_takeover_keywords: list[str] = Field(
        default=["人工", "投诉", "退款", "举报", "差评", "维权", "起诉"],
        alias="HUMAN_TAKEOVER_KEYWORDS"
    )
    max_auto_reply_count: int = 5  # 同一会话最大自动回复次数，超过转人工

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()