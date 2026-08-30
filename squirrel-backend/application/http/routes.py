from fastapi import APIRouter, FastAPI

from application.routes.health import router as health_router
from application.routes.logs import router as logs_router
from domains.playlist.interfaces.http import router as playlist_router
from domains.rss.interfaces.http import router as rss_router
from domains.subscription.interfaces.http import router as subscription_router
from domains.system.interfaces.http.system_config import router as system_config_router
from domains.user.interfaces.http import router as user_router
from domains.user.interfaces.http.search import router as search_router
from domains.video.interfaces.http import router as video_router
from domains.video.interfaces.http.clip_marker import router as video_clip_marker_router
from domains.video.interfaces.http.creators import router as creator_router
from domains.video.interfaces.http.history import router as video_history_router
from domains.video.interfaces.http.interaction import router as video_interaction_router
from infrastructure.scheduling.routes import router as scheduler_router
from infrastructure.site_catalog.routes.site_cookies_bulk_import import router as site_cookies_router
from infrastructure.site_catalog.routes.site_cookies_cookiecloud import router as site_cookiecloud_router
from infrastructure.site_catalog.routes.site_cookies_single_upload import router as site_cookie_upload_router
from infrastructure.site_catalog.routes.sites_catalog import router as sites_router
from infrastructure.site_catalog.routes.sites_connectivity_all import router as sites_connectivity_all_router
from infrastructure.site_catalog.routes.sites_connectivity_batch import router as sites_connectivity_batch_router
from infrastructure.site_catalog.routes.sites_connectivity_single import router as sites_connectivity_single_router
from infrastructure.site_catalog.routes.sites_login import router as sites_login_router
from infrastructure.site_catalog.routes.sites_youtube_oauth import router as sites_youtube_oauth_router

site_operations_router = APIRouter(prefix='/api/sites', tags=['Sites'])
site_operations_router.include_router(sites_connectivity_all_router)
site_operations_router.include_router(sites_connectivity_batch_router)
site_operations_router.include_router(sites_connectivity_single_router)
site_operations_router.include_router(sites_login_router)
site_operations_router.include_router(sites_youtube_oauth_router)

site_cookie_operations_router = APIRouter(prefix='/api/site-cookies', tags=['Site Cookies'])
site_cookie_operations_router.include_router(site_cookies_router)
site_cookie_operations_router.include_router(site_cookie_upload_router)
site_cookie_operations_router.include_router(site_cookiecloud_router)

ROUTERS: tuple[APIRouter, ...] = (
    health_router,
    video_router,
    creator_router,
    video_clip_marker_router,
    video_history_router,
    video_interaction_router,
    subscription_router,
    user_router,
    search_router,
    playlist_router,
    rss_router,
    system_config_router,
    sites_router,
    site_operations_router,
    site_cookie_operations_router,
    scheduler_router,
    logs_router,
)


def register_routers(application: FastAPI) -> None:
    for router in ROUTERS:
        application.include_router(router)
