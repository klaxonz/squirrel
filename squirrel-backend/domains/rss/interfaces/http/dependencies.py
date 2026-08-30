from fastapi import Request

from domains.rss.application.services.service import RssService


def get_rss_service(request: Request) -> RssService:
    return request.app.state.rss_service
