"""
健康检查路由
用于 Docker 容器健康检查和服务监控
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, status
from sqlalchemy import text

from core.cache import redis_client
from core.database import engine
from core.startup_dependencies import list_optional_startup_issues

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    
    检查项：
    1. API 服务状态
    2. 数据库连接
    3. Redis 连接
    
    Returns:
        健康状态信息
    """
    health_status = {
        "status": "healthy",
        "checks": {
            "api": "ok",
            "database": "unknown",
            "redis": "unknown",
            "startup_optional": "ok",
        }
    }

    startup_issues = list_optional_startup_issues()
    if startup_issues:
        health_status["checks"]["startup_optional"] = "degraded"
        health_status["startup_optional_issues"] = [
            {"name": issue.name, "error": issue.error}
            for issue in startup_issues
        ]
        health_status["status"] = "degraded"
    
    # 检查数据库连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health_status["checks"]["database"] = "ok"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        health_status["checks"]["database"] = "error"
        health_status["status"] = "degraded"
    
    # 检查 Redis 连接
    try:
        redis_client.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = "error"
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """
    就绪检查端点
    
    用于 Kubernetes 等编排系统的就绪探针
    
    Returns:
        就绪状态
    """
    # 检查关键服务是否就绪
    try:
        # 检查数据库
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 检查 Redis
        redis_client.ping()
        
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e)}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    存活检查端点
    
    用于 Kubernetes 等编排系统的存活探针
    仅检查 API 服务本身是否响应
    
    Returns:
        存活状态
    """
    return {"status": "alive"}

