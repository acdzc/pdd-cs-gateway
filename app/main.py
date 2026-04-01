"""
拼多多客服网关 - FastAPI 应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.config import get_settings
from app.pdd.webhook import router as webhook_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"PDD Client ID: {settings.pdd_client_id[:8]}..." if settings.pdd_client_id else "PDD Client ID not configured")

    # 启动时初始化
    yield

    # 关闭时清理
    logger.info("Shutting down...")


# 创建应用
settings = get_settings()
app = FastAPI(
    title="拼多多客服网关",
    description="拼多多客服消息处理网关，支持自动回复、飞书通知、OpenClaw AI 集成",
    version=settings.app_version,
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.3f}s"
    )
    return response


# 注册路由
app.include_router(webhook_router, prefix="/api")


# 健康检查
@app.get("/health", tags=["health"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/", tags=["root"])
async def root():
    """根路径"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )