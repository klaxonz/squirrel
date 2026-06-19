import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger('squirrel.access')


class AccessLogMiddleware:
    """Application-level access logger that runs inside request context."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        status_code = 500

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message['type'] == 'http.response.start':
                status_code = int(message['status'])
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            client = scope.get('client')
            client_label = f'{client[0]}:{client[1]}' if client else '-'

            logger.info(
                'access client=%s method=%s path=%s status=%s duration_ms=%s',
                client_label,
                scope.get('method', '-'),
                scope.get('path', '-'),
                status_code,
                duration_ms,
            )
