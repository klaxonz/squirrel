"""Request context middleware for trace propagation."""

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from utils.trace import bind_trace_id, generate_trace_id, reset_trace_id


class RequestContextMiddleware:
    """Attach a trace_id to each HTTP request and response."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        trace_id = headers.get("x-trace-id") or generate_trace_id()
        token = bind_trace_id(trace_id)
        scope.setdefault("state", {})["trace_id"] = trace_id

        async def send_with_trace_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Trace-Id"] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        finally:
            reset_trace_id(token)


TraceMiddleware = RequestContextMiddleware
