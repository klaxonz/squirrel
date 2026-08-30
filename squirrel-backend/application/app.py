from fastapi import FastAPI

from application.http.errors import EXCEPTION_HANDLERS
from application.http.middleware import register_middleware
from application.http.routes import register_routers
from application.http.static_assets import mount_static_assets
from application.lifespan import lifespan
from domains.rss.application.services.service import RssService
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.application.services.service import SubscriptionService
from domains.user.application.services.config import UserConfigService
from domains.user.application.services.search.suggestion_service import SearchSuggestionService
from domains.user.application.services.service import UserService
from domains.video.application.services.service import VideoService


def create_app() -> FastAPI:
    app = FastAPI(exception_handlers=EXCEPTION_HANDLERS, lifespan=lifespan)
    crawl_tasks = CrawlTaskService()
    user_config = UserConfigService()
    search_suggestions = SearchSuggestionService(get_user_config=user_config.get_config)
    app.state.video_service = VideoService(crawl_tasks=crawl_tasks, user_config=user_config)
    app.state.subscription_service = SubscriptionService(
        video_service=app.state.video_service,
        crawl_tasks=crawl_tasks,
        user_config=user_config,
        invalidate_search_suggestions=search_suggestions.invalidate_users_for_subscription,
    )
    app.state.user_service = UserService()
    app.state.user_config_service = user_config
    app.state.search_suggestion_service = search_suggestions
    app.state.rss_service = RssService()
    register_middleware(app)
    register_routers(app)
    mount_static_assets(app)
    return app
