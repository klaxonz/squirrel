from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

from .dependencies import get_music_service

router = APIRouter()


@router.get('/search')
async def search_music(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    return response.success(await music_service.search_tracks(current_user.id, normalized_query, page, page_size))


@router.get('/search/artists')
async def search_music_artists(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(10, ge=1, le=30, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    return response.success(await music_service.search_artists(current_user.id, normalized_query, page, page_size))


@router.get('/search/albums')
async def search_music_albums(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(12, ge=1, le=30, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    return response.success(await music_service.search_albums(current_user.id, normalized_query, page, page_size))


@router.get('/search/default')
async def get_music_default_search(
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_default_search_keyword(current_user.id))


@router.get('/search/hot')
async def list_music_hot_searches(
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_hot_searches(current_user.id))


@router.get('/search/suggest')
async def suggest_music_search(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    return response.success(await music_service.search_suggestions(current_user.id, normalized_query))


@router.get('/search/complex')
async def search_music_complex(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')
    return response.success(await music_service.get_complex_search(current_user.id, normalized_query))
