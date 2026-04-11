import logging
from fastapi import Query, APIRouter, Request, HTTPException, Depends, Response, Body
from fastapi.responses import PlainTextResponse
import common.response as response
from core.exceptions.video_exceptions import UnsupportedDomainError, VideoUrlExtractionError
from models.user import User
from schemas.video.request.video import SortBy
from services import video_service
from services.site_catalog_service import save_site_overrides
from typing import List
from utils.site_catalog import SiteCatalog
from core.site_config_manager import get_effective_site_catalog
from plugins.manager import get_plugin_manager
from utils.jwt_helper import get_current_user
from utils.url_helper import normalize_domain

logger = logging.getLogger()

router = APIRouter(tags=['频道视频接口'])


def _video_domain(url: str) -> str:
    return normalize_domain(url) or ''


@router.get("/api/video/url")
def get_video_url(
        video_id: int = Query(None, description="视频ID"),
        force_refresh: bool = Query(False, description="强制刷新播放链接（跳过服务端缓存）", alias="force_refresh"),
        client_type: str | None = Query(None, description="客户端类型（desktop 等）", alias="client_type"),
):
    try:
        if video_id is None:
            return response.param_error("参数错误 (VIDEO_ID_REQUIRED)")

        video_urls = video_service.get_video_url(video_id, force_refresh=force_refresh, client_type=client_type)
        # 校验是否成功提取到可播放链接（支持 DASH 的 mpd_url 返回）
        has_video = getattr(video_urls, 'video_url', None)
        has_audio = getattr(video_urls, 'audio_url', None)
        has_mpd = getattr(video_urls, 'mpd_url', None)
        if not video_urls or (not has_video and not has_audio and not has_mpd):
            return response.not_found("无法获取播放链接 (NO_STREAM_URL)")
        return response.success(video_urls)

    except UnsupportedDomainError as e:
        logger.warning(f"Unsupported domain for video {video_id}: {e}")
        return response.param_error(f"{e} (UNSUPPORTED_DOMAIN)")
    except VideoUrlExtractionError as e:
        logger.error(f"Video URL extraction failed for {video_id}: {e}")
        return response.server_error(f"{e} (EXTRACT_FAILED)")
    except ValueError as e:
        # 包括视频不存在等
        msg = str(e)
        if 'not found' in msg.lower():
            return response.not_found("视频不存在 (VIDEO_NOT_FOUND)")
        logger.error(f"Invalid request for get_video_url: {e}")
        return response.param_error("请求不合法 (BAD_REQUEST)")
    except Exception as e:
        logger.exception(f"Unexpected error in get_video_url for video_id={video_id}: {e}")
        return response.server_error("服务器内部错误 (SERVER_ERROR)")


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
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        with_total: bool = Query(False, alias="withTotal", description="是否返回 total（会额外执行 count 查询）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        current_user: User = Depends(get_current_user)
):

    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None

    if hasattr(current_user, '_cached_config'):
        logger.info(f"[Performance] Route: Using cached user config")
    
    videos, total_counts = video_service.list_videos(
        current_user.id, query, subscription_id, category, sort_by, nsfw, domains_list, page, page_size, with_total=with_total
    )

    result = response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos
    })

    return result


@router.get("/api/video/counts")
def get_video_counts(
        query: str = Query(None, description="搜索关键字"),
        subscription_id: int = Query(None, description="订阅ID"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        current_user: User = Depends(get_current_user)
):
    """获取视频各类别计数的独立接口（可单独缓存）"""

    domains_list: List[str] | None = None
    if site:
        resolved = SiteCatalog.resolve_domains(site)
        domains_list = resolved if resolved else None
    
    counts = video_service.get_video_counts(
        current_user.id, query, subscription_id, nsfw, domains_list
    )
    
    return response.success(counts)


@router.get("/api/video/random")
def get_random_video(
        category: str = Query('all', description="类别：all|read|unread|preview|liked|later"),
        subscription_id: int = Query(None, description="订阅ID"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        site: str = Query(None, description="站点过滤：例如 youtube、bilibili 等（支持别名）"),
        query: str = Query(None, description="搜索关键字"),
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
        query=query
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
        fmt: str = Query("srt", description="返回格式：目前仅支持 srt"),
        current_user: User = Depends(get_current_user)
):
    if fmt.lower() != "srt":
        raise HTTPException(status_code=400, detail="Only srt format is supported")

    video = video_service.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    domain = _video_domain(video.url)
    try:
        result = get_plugin_manager().gateway.invoke(
            'fetch_subtitles',
            domain=domain,
            payload={
                'video_id': video.id,
                'url': video.url,
                'title': getattr(video, 'title', None),
                'duration': getattr(video, 'duration', None),
                'lang': lang,
                'fmt': fmt,
            },
        )
        if not result.ok or not isinstance(result.data, dict):
            raise HTTPException(status_code=400, detail="Subtitles provider not available for this domain")
        srt_text = str(result.data.get('content') or '')
        fallback_filename = f'{video.id}.{lang}.srt' if lang else f'{video.id}.srt'
        filename = str(result.data.get('filename') or fallback_filename)
        media_type = str(result.data.get('media_type') or 'text/plain; charset=utf-8')
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


@router.get("/api/video/mpd")
def get_video_mpd(
        video_id: int = Query(..., description="视频ID"),
        direct: bool = Query(False, description="是否返回直链 MPD"),
):
    """
    根据不同站点生成 MPD（站点适配在 sites/* 中实现）
    """
    if video_id is None:
        raise HTTPException(status_code=400, detail="video_id is required")

    video = video_service.get_video_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    direct_enabled = direct if isinstance(direct, bool) else False
    domain = _video_domain(video.url)
    try:
        payload = {
            'video_id': video.id,
            'url': video.url,
            'title': getattr(video, 'title', None),
            'duration': getattr(video, 'duration', None),
        }
        if direct_enabled:
            payload['direct_playback'] = True

        result = get_plugin_manager().gateway.invoke(
            'build_mpd',
            domain=domain,
            payload=payload,
        )
        if not result.ok or not isinstance(result.data, dict):
            raise HTTPException(status_code=400, detail="MPD builder not available for this domain")
        mpd_xml = str(result.data.get('content') or '')
        if not mpd_xml:
            raise HTTPException(status_code=500, detail="Failed to build MPD")
        return Response(
            content=mpd_xml,
            media_type=str(result.data.get('media_type') or 'application/dash+xml'),
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache"
            }
        )
    except HTTPException:
        raise
    except ValueError as e:
        # 未注册对应站点的 MPD 构建器
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Failed to build MPD")
        raise HTTPException(status_code=500, detail="Internal Server Error")


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
