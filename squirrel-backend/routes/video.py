import logging
from fastapi import Query, APIRouter, Request, HTTPException, Depends, Body
from fastapi.responses import PlainTextResponse
import common.response as response
from models.user import User
from schemas.video.request.video import RemoteVideoSaveRequest, SortBy
from services import video_service
from services.site_catalog_service import save_site_overrides
from typing import List
from utils.site_catalog import SiteCatalog
from core.site_config_manager import get_effective_site_catalog
from site_runtimes.manager import get_site_runtime_manager
from utils.jwt_helper import get_current_user
from utils.url_helper import normalize_domain

logger = logging.getLogger()

router = APIRouter(tags=['频道视频接口'])


def _video_domain(url: str) -> str:
    return normalize_domain(url) or ''


@router.post("/api/video/remote/save")
def save_remote_video(
        data: RemoteVideoSaveRequest,
        current_user: User = Depends(get_current_user)
):
    try:
        video = video_service.save_remote_video(data.model_dump())
        return response.success(video_service.get_video(current_user.id, video.id))
    except ValueError as exc:
        return response.param_error(str(exc))
    except Exception:
        logger.exception("Failed to save remote video")
        return response.server_error("保存远端视频失败")


@router.get("/api/video/detail")
def get_video(
        video_id: int = Query(None, description="视频ID"),
        current_user: User = Depends(get_current_user)
):
    video = video_service.get_video(current_user.id, video_id)
    return response.success(video)


@router.get("/api/video/list")
def get_videos(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        category: str = Query('all', description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        special: str = Query("all", description="特别关注过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        with_total: bool = Query(False, alias="withTotal", description="是否返回 total（会额外执行 count 查询）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        time_range: str = Query("all", description="时间范围: all|today|week|month|year"),
        duration: str = Query("all", description="时长: all|short|medium|long"),
        content_type: str = Query("all", description="内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR"),
        current_user: User = Depends(get_current_user)
):

    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None

    if hasattr(current_user, '_cached_config'):
        logger.info(f"[Performance] Route: Using cached user config")

    videos, total_counts = video_service.list_videos(
        current_user.id, query, subscription_id, category, sort_by, nsfw, domains_list, page, page_size,
        with_total=with_total, time_range=time_range, duration=duration, content_type=content_type, special=special,
    )

    result = response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos
    })

    return result


@router.get("/api/video/random")
def get_random_video(
        category: str = Query('all', description="类别：all|read|unread|preview|liked|later"),
        subscription_id: int = Query(None, description="订阅ID"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        query: str = Query(None, description="搜索关键字"),
        time_range: str = Query("all", description="时间范围: all|today|week|month|year"),
        duration: str = Query("all", description="时长: all|short|medium|long"),
        content_type: str = Query("all", description="内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR"),
        current_user: User = Depends(get_current_user)
):
    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None

    video = video_service.get_random_video(
        current_user.id,
        category=category,
        subscription_id=subscription_id,
        nsfw=nsfw,
        domains=domains_list,
        query=query,
        time_range=time_range,
        duration=duration,
        content_type=content_type,
    )
    if not video:
        return response.not_found("未找到符合条件的视频")

    # 返回完整视频详情，便于前端直接播放
    detail = video_service.get_video(current_user.id, video.id)
    return response.success(detail)


@router.get("/api/video/proxy")
async def proxy_video(domain: str, url: str, request: Request, referer: str | None = None):
    """代理视频文件，用于解决跨域问题"""
    from core.streaming.proxy import VideoProxy

    proxy = VideoProxy(request, domain=domain)
    return await proxy.handle_stream(url, referer=referer)


@router.get("/api/video/subtitles")
def get_video_subtitles(
        video_id: int = Query(..., description="视频ID"),
        lang: str | None = Query(None, description="字幕语言代码；留空时走站点默认值"),
        fmt: str = Query("srt", description="返回格式：支持 srt、vtt"),
        current_user: User = Depends(get_current_user)
):
    normalized_fmt = fmt.lower()
    if normalized_fmt not in {'srt', 'vtt'}:
        raise HTTPException(status_code=400, detail='Only srt and vtt formats are supported')

    video = video_service.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    domain = _video_domain(video.url)
    try:
        result = get_site_runtime_manager().gateway.invoke(
            'fetch_subtitles',
            domain=domain,
            payload={
                'video_id': video.id,
                'url': video.url,
                'title': getattr(video, 'title', None),
                'duration': getattr(video, 'duration', None),
                'lang': lang,
                'fmt': normalized_fmt,
            },
        )
        if not result.ok or not isinstance(result.data, dict):
            error = getattr(result, 'error', None)
            error_message = str(getattr(error, 'message', '') or '').strip()
            if 'No subtitles available' in error_message:
                raise HTTPException(status_code=404, detail='No subtitles available')
            if 'No runtime route found for capability' in error_message:
                raise HTTPException(status_code=400, detail='Subtitles provider not available for this domain')
            if error_message:
                raise HTTPException(status_code=400, detail=error_message)
            raise HTTPException(status_code=400, detail='Subtitles provider not available for this domain')
        srt_text = str(result.data.get('content') or '')
        fallback_ext = normalized_fmt
        fallback_filename = f'{video.id}.{lang}.{fallback_ext}' if lang else f'{video.id}.{fallback_ext}'
        filename = str(result.data.get('filename') or fallback_filename)
        fallback_media_type = 'text/vtt; charset=utf-8' if normalized_fmt == 'vtt' else 'text/plain; charset=utf-8'
        media_type = str(result.data.get('media_type') or fallback_media_type)
        return PlainTextResponse(
            content=srt_text,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\""
            }
        )
    except HTTPException:
        raise
    except ValueError as e:
        detail = str(e)
        if 'No subtitles available' in detail:
            raise HTTPException(status_code=404, detail="No subtitles available")
        raise HTTPException(status_code=400, detail=detail)
    except Exception:
        logger.exception('Subtitles fetch failed')
        raise HTTPException(status_code=500, detail="Server error")


@router.get("/api/sites")
def get_sites_catalog():
    """返回完整站点配置（label, domains, aliases, enabled）。"""
    return response.success(get_effective_site_catalog())


@router.put("/api/sites")
def update_sites_catalog(payload: dict = Body(...)):
    """保存页面编辑后的站点 override 配置。"""
    sites_payload = payload.get('sites') if isinstance(payload, dict) else None
    if not isinstance(sites_payload, dict):
        return response.param_error('sites 必须为对象')

    try:
        catalog = save_site_overrides(sites_payload)
        return response.success(catalog, msg="站点配置已更新")
    except ValueError as exc:
        return response.param_error(str(exc))
    except Exception:
        logger.exception("Failed to update site catalog")
        return response.server_error("保存站点配置失败")


