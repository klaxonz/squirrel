from fastapi import FastAPI

from application.http.errors import EXCEPTION_HANDLERS
from application.http.middleware import register_middleware
from application.http.routes import register_routers
from application.http.static_assets import mount_static_assets
from application.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=EXCEPTION_HANDLERS, lifespan=lifespan)
    register_middleware(app)
    register_routers(app)
    mount_static_assets(app)
    return app
