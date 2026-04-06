from fastapi import FastAPI

from squirrel_cf_bypass.app.api.routes import router
from squirrel_cf_bypass.app.core.browser_solver import BrowserSolver
from squirrel_cf_bypass.app.core.cache import ClearanceCache
from squirrel_cf_bypass.app.core.service import CloudflareBypassService
from squirrel_cf_bypass.app.core.session_pool import SessionPool


class _MissingSolver:
    ready = False

    async def fetch_html(self, *args, **kwargs):
        return None


def create_app(solver=None) -> FastAPI:
    app = FastAPI(title='squirrel-cf-bypass')
    app.state.bypass_service = CloudflareBypassService(
        solver=solver or BrowserSolver(),
        cache=ClearanceCache(ttl_seconds=900),
        session_pool=SessionPool(ttl_seconds=300, max_sessions=32),
        ttl_seconds=900,
    )
    app.include_router(router)
    return app


app = create_app()
