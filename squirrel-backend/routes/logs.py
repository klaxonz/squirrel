import logging
from typing import Optional

from fastapi import Query, APIRouter, Depends

from models.user import User
from utils.jwt_helper import get_current_user
import common.response as response
from services import log_service

logger = logging.getLogger()
router = APIRouter(tags=['日志管理'])


@router.get("/api/logs/files")
def get_log_files(current_user: User = Depends(get_current_user)):
    """获取所有日志文件列表"""
    try:
        files = log_service.get_log_files()
        return response.success(files)
    except Exception as e:
        logger.exception(f"Failed to get log files: {e}")
        return response.server_error("获取日志文件列表失败")


@router.get("/api/logs/query")
def query_logs(
    filename: str = Query('app.log', description="日志文件名"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    level: Optional[str] = Query(None, description="日志级别 (INFO, WARNING, ERROR, DEBUG)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(500, ge=1, le=2000, alias="pageSize", description="每页数量"),
    current_user: User = Depends(get_current_user)
):
    """
    查询日志内容
    
    支持按关键词和日志级别过滤
    """
    try:
        start_line = (page - 1) * page_size
        
        lines, total_count, has_more = log_service.read_log_lines(
            filename=filename,
            keyword=keyword,
            level=level,
            start_line=start_line,
            limit=page_size
        )
        
        return response.success({
            'logs': lines,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'has_more': has_more
        })
    
    except Exception as e:
        logger.exception(f"Failed to query logs: {e}")
        return response.server_error("查询日志失败")
