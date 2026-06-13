import logging

from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from services.system.logs import LogService
from services.user.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/logs", tags=["Log Management"])


def get_log_service() -> LogService:
    return LogService()


@router.get("/files")
def get_log_files(
    current_user: User = Depends(get_current_user),
    svc: LogService = Depends(get_log_service),
):
    """Get all log file list"""
    try:
        files = svc.get_log_files()
        return response.success(files)
    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to get log files: %s", e)
        return response.server_error("获取日志文件列表失败")


@router.get("/query")
def query_logs(
    filename: str = Query("app.log", description="Log file name"),
    keyword: str | None = Query(None, description="Search keyword"),
    level: str | None = Query(None, description="Log level (INFO, WARNING, ERROR, DEBUG)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(500, ge=1, le=2000, alias="pageSize", description="Page size"),
    current_user: User = Depends(get_current_user),
    svc: LogService = Depends(get_log_service),
):
    """Query log contents

    Supports filtering by keyword and log level
    """
    try:
        start_line = (page - 1) * page_size

        lines, total_count, has_more = svc.read_log_lines(
            filename=filename,
            keyword=keyword,
            level=level,
            start_line=start_line,
            limit=page_size,
        )

        return response.success({
            "logs": lines,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
        })

    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to query logs: %s", e)
        return response.server_error("查询日志失败")
