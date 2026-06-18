"""Health check routes
Used for Docker container health checks and service monitoring
"""
import logging
from typing import Any

from fastapi import APIRouter, Request, status
from sqlalchemy import text

from application.startup_health import StartupHealth
from infrastructure.cache.redis_client import redis_client
from infrastructure.database.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(request: Request) -> dict[str, Any]:
    """Health check endpoint

    Checks:
    1. API service status
    2. Database connection
    3. Redis connection
    4. Optional startup dependencies

    Returns:
        Health status information

    """
    health_status = {
        "status": "healthy",
        "checks": {
            "api": "ok",
            "database": "unknown",
            "redis": "unknown",
            "startup_optional": "ok",
        },
    }

    startup_issues: StartupHealth = getattr(request.app.state, "startup_health", None)
    issues = startup_issues.list() if startup_issues is not None else []
    if issues:
        health_status["checks"]["startup_optional"] = "degraded"
        health_status["startup_optional_issues"] = [
            {"name": issue.name, "error": issue.error}
            for issue in issues
        ]
        health_status["status"] = "degraded"

    # 检查数据库连接
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health_status["checks"]["database"] = "ok"
    except (OSError, ConnectionError, ValueError, TypeError) as e:
        logger.warning("Database health check failed: %s", e)
        health_status["checks"]["database"] = "error"
        health_status["status"] = "degraded"

    # 检查 Redis 连接
    try:
        redis_client.ping()
        health_status["checks"]["redis"] = "ok"
    except (OSError, ConnectionError, ValueError, TypeError) as e:
        logger.warning("Redis health check failed: %s", e)
        health_status["checks"]["redis"] = "error"
        health_status["status"] = "degraded"

    return health_status


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint

    Used as readiness probe for Kubernetes and similar orchestration systems

    Returns:
        Readiness status

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
        # API boundary -- convert to HTTP error response
        logger.error("Readiness check failed: %s", e)
        return {"status": "not ready", "error": str(e)}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """Liveness check endpoint

    Used as liveness probe for Kubernetes and similar orchestration systems
    Only checks if the API service itself is responding

    Returns:
        Liveness status

    """
    return {"status": "alive"}

