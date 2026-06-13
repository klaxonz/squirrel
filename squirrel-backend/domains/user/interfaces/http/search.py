from fastapi import APIRouter, Depends, Query

from shared_kernel.application import response
from domains.user.domain.models.user import User
from domains.user.application.services.auth import get_current_user
from domains.user.application.services.search.suggestion_service import SearchSuggestionService, search_suggestion_service

router = APIRouter(prefix="/api/search", tags=["搜索建议接口"])


def get_search_suggestion_service() -> SearchSuggestionService:
    return search_suggestion_service


@router.get("/suggestions")
def get_search_suggestions(
    query: str = Query(None, description="联想关键词"),
    scope: str = Query("home", description="搜索场景：home/subscribed/history"),
    limit: int = Query(8, ge=1, le=20, description="返回数量上限"),
    current_user: User = Depends(get_current_user),
    svc: SearchSuggestionService = Depends(get_search_suggestion_service),
):
    items = svc.list_search_suggestions(
        current_user.id,
        query=query,
        scope=scope,
        limit=limit,
    )
    return response.success({
        "items": items,
        "scope": scope,
        "query": query,
    })
