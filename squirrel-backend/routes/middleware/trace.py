"""链路追踪中间件

为每个 HTTP 请求生成或提取 trace_id，并在请求处理过程中保持 trace_id 的传递。

功能：
1. 从请求头 X-Trace-Id 中提取 trace_id（如果客户端提供）
2. 如果没有提供，则自动生成新的 trace_id
3. 将 trace_id 设置到当前上下文中，供日志使用
4. 在响应头中返回 X-Trace-Id
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.trace import generate_trace_id, set_trace_id

logger = logging.getLogger()


class TraceMiddleware(BaseHTTPMiddleware):
    """链路追踪中间件
    
    为每个 HTTP 请求添加 trace_id 支持
    """
    
    async def dispatch(self, request: Request, call_next):
        # 从请求头中提取 trace_id，如果没有则生成新的
        trace_id = request.headers.get("X-Trace-Id") or generate_trace_id()
        
        # 设置到当前上下文
        set_trace_id(trace_id)
        
        # 处理请求
        response: Response = await call_next(request)
        
        # 在响应头中添加 trace_id
        response.headers["X-Trace-Id"] = trace_id
        
        return response

