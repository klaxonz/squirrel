import logging
import os
import re
import glob
import tempfile

import requests
from fastapi import Query, APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import PlainTextResponse
from yt_dlp import YoutubeDL
from xml.etree import ElementTree as ET

import common.response as response
from common.video_stream import VideoStreamHandler
from core import download_config, config
from sites.downloader import DownloaderFactory
from meta.factory import VideoFactory
from models.user import User
from schemas.video import DownloadVideoRequest, SortBy
from schemas.proxy import VideoProxyRequest
from services import video_service, subscription_video_service, subscription_service
from services.proxy_service import ProxyServiceFactory
from utils.jwt_helper import get_current_user
from handlers.video_url.base import UnsupportedDomainError, VideoUrlExtractionError

logger = logging.getLogger()

router = APIRouter(tags=['频道视频接口'])


@router.get("/api/video/url")
def get_video_url(
        video_id: int = Query(None, description="视频ID")
):
    try:
        if video_id is None:
            return response.param_error("参数错误 (VIDEO_ID_REQUIRED)")

        video_urls = video_service.get_video_url(video_id)
        # 校验是否成功提取到可播放链接（支持 DASH 的 mpd_url 返回）
        has_video = getattr(video_urls, 'video_url', None)
        has_audio = getattr(video_urls, 'audio_url', None)
        has_mpd = getattr(video_urls, 'mpd_url', None)
        if not video_urls or (not has_video and not has_audio and not has_mpd):
            return response.not_found("无法获取播放链接 (NO_STREAM_URL)")
        return response.success(video_urls)

    except UnsupportedDomainError as e:
        logger.warning(f"Unsupported domain for video {video_id}: {e}")
        return response.param_error("不支持的域名 (UNSUPPORTED_DOMAIN)")
    except VideoUrlExtractionError as e:
        logger.error(f"Video URL extraction failed for {video_id}: {e}")
        return response.server_error("播放链接提取失败 (EXTRACT_FAILED)")
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
        category: str = Query(None, description="阅读状态: all, read, unread, preview, like"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        nsfw: str = Query("all", description="NSFW 过滤: all|yes|no", pattern=r"^(all|yes|no)$"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
        current_user: User = Depends(get_current_user)
):
    videos, total_counts, counts = video_service.list_videos(
        current_user.id, query, subscription_id, category, sort_by, nsfw, page, page_size
    )
    return response.success({
        "total": total_counts,
        "page": page,
        "pageSize": page_size,
        "data": videos,
        "counts": counts
    })


@router.post("/api/video/download")
def download_video(req: DownloadVideoRequest):
    video_service.download_video(req.video_id)
    return response.success()


@router.get("/api/video/play/{video_id}")
def play_video(request: Request, video_id: int):
    video = video_service.get_video_by_id(video_id)
    downloader = DownloaderFactory.create_downloader(video.url)
    video_info = downloader.get_video_info()
    video = VideoFactory.create_video(video.url, video_info)
    subscription_video = subscription_video_service.get_subscription_video_by_video_id(video.id)
    subscription = subscription_service.get_subscription_by_id(subscription_video.subscription_id)
    output_dir = download_config.get_download_full_path(subscription.name, video.season)
    filename = download_config.get_valid_filename(video.title)
    video_path = VideoStreamHandler.find_video_file(output_dir, filename)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    return VideoStreamHandler.create_stream_response(request, video_path)


@router.get("/api/video/proxy")
async def proxy_video(domain: str, url: str, request: Request):
    """代理视频文件，用于解决跨域问题"""
    proxy_request = VideoProxyRequest(domain=domain, url=url)
    proxy_service = ProxyServiceFactory.get_proxy_service()
    return await proxy_service.handle_proxy_request(proxy_request, request)


@router.get("/api/video/proxy/domains")
def get_supported_domains():
    """获取支持的代理域名列表"""
    proxy_service = ProxyServiceFactory.get_proxy_service()
    domains = proxy_service.get_supported_domains()
    return response.success({
        "domains": domains,
        "count": len(domains)
    })


@router.get("/api/video/proxy/health")
async def get_proxy_health():
    """获取代理服务健康状态"""
    proxy_service = ProxyServiceFactory.get_proxy_service()
    health_status = await proxy_service.get_proxy_health_status()
    return response.success({
        "health_status": health_status,
        "overall_healthy": all(health_status.values())
    })


@router.get("/api/video/subtitles")
def get_video_subtitles(
        video_id: int = Query(..., description="视频ID"),
        lang: str = Query("ai-zh", description="字幕语言代码（b站如 ai-zh/zh/zh-CN/en 等）"),
        fmt: str = Query("srt", description="返回格式：目前仅支持 srt"),
        current_user: User = Depends(get_current_user)
):
    """获取视频字幕。

    仅支持 bilibili.com：优先返回 AI 中文（ai-zh），将 B站字幕JSON转换为SRT 纯文本返回。
    """
    if fmt.lower() != "srt":
        raise HTTPException(status_code=400, detail="Only srt format is supported")

    # 读取视频信息
    video = video_service.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if 'bilibili.com' not in video.url:
        raise HTTPException(status_code=400, detail="Subtitles not supported for this domain")

    # 优先尝试：使用 yt-dlp 直接拉取并转换字幕为 SRT
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': False,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [lang],
                'subtitlesformat': 'srt',
                'postprocessors': [{
                    'key': 'FFmpegSubtitlesConvertor',
                    'format': 'srt'
                }],
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }

            cookie_file_path = config.get_cookies_file_path()
            if cookie_file_path and 'youtube.com' not in video.url:
                ydl_opts['cookiefile'] = cookie_file_path

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])

            # 查找生成的 SRT 文件
            srt_files = glob.glob(os.path.join(tmpdir, '*.srt'))
            preferred = None
            for path in srt_files:
                filename = os.path.basename(path)
                if f'.{lang}.' in filename or filename.endswith(f'.{lang}.srt'):
                    preferred = path
                    break
            target_path = preferred or (srt_files[0] if srt_files else None)

            if target_path:
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as rf:
                    srt_text = rf.read()
                bvid_match = re.search(r'(BV[\w-]+)', video.url) if 'bilibili.com' in video.url else None
                filename = f"{(bvid_match.group(1) if bvid_match else video.id)}.{lang}.srt"
                return PlainTextResponse(
                    content=srt_text,
                    media_type="text/plain; charset=utf-8",
                    headers={
                        "Content-Disposition": f"inline; filename=\"{filename}\""
                    }
                )
    except Exception:
        logger.info('yt-dlp 字幕抓取失败，尝试使用备用方案 (bilibili API)')


@router.get("/api/video/mpd")
def get_video_mpd(
        video_id: int = Query(..., description="视频ID"),
):
    """
    获取 Bilibili 视频的 DASH MPD 文件。
    """
    if video_id is None:
        raise HTTPException(status_code=400, detail="video_id is required")

    video = video_service.get_video_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    from sites.bilibili.handler import fetch_html, extract_playinfo_from_html
    html = fetch_html(video.url)
    if html is None:
        raise HTTPException(status_code=500, detail="Failed to fetch video page")

    play_info = extract_playinfo_from_html(html)
    if not play_info or 'data' not in play_info or 'dash' not in play_info['data']:
        raise HTTPException(status_code=500, detail="Failed to extract play info")

    dash_data = play_info['data']['dash']
    duration = dash_data.get('duration')
    min_buffer_time = dash_data.get('minBufferTime')

    mpd = ET.Element("MPD", xmlns="urn:mpeg:dash:schema:mpd:2011")
    if min_buffer_time:
        mpd.set("minBufferTime", f"PT{min_buffer_time}S")
    if duration:
        mpd.set("mediaPresentationDuration", f"PT{duration}S")
    mpd.set("type", "static")
    mpd.set("profiles", "urn:mpeg:dash:profile:isoff-on-demand:2011")

    period = ET.SubElement(mpd, "Period")

    # Video streams
    if 'video' in dash_data:
        # 仅选择浏览器常见可播放的 H.264/AVC 轨道，避免选中 HEVC/AV1 导致下载很多却无法解码
        video_streams = [v for v in dash_data['video'] if 'codecs' in v and ('avc' in v['codecs'] or 'avc1' in v['codecs'] or 'h264' in v['codecs'])]
        if not video_streams:
            video_streams = dash_data['video']  # 兜底：若没有 avc，则放开（由 dash.js 自行选择）

        video_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="video", mimeType="video/mp4")
        for video_stream in video_streams:
            representation = ET.SubElement(video_adaptation_set, "Representation")
            representation.set("id", str(video_stream['id']))
            representation.set("codecs", video_stream['codecs'])
            representation.set("width", str(video_stream['width']))
            representation.set("height", str(video_stream['height']))
            if 'frameRate' in video_stream:
                representation.set("frameRate", str(video_stream['frameRate']))
            representation.set("bandwidth", str(video_stream['bandwidth']))

            base_url = ET.SubElement(representation, "BaseURL")
            # 通过后端代理避免跨域问题
            proxied_video_url = f"/api/video/proxy?domain=bilibili.com&url=" + requests.utils.quote(video_stream['baseUrl'], safe='')
            base_url.text = proxied_video_url

            segment_base = ET.SubElement(representation, "SegmentBase")
            segment_base.set("indexRange", video_stream['SegmentBase']['indexRange'])
            initialization = ET.SubElement(segment_base, "Initialization")
            initialization.set("range", video_stream['SegmentBase']['Initialization'])

    # Audio streams
    if 'audio' in dash_data:
        # 音频一般为 AAC（mp4a），保持全部
        audio_adaptation_set = ET.SubElement(period, "AdaptationSet", contentType="audio", mimeType="audio/mp4")
        for audio_stream in dash_data['audio']:
            representation = ET.SubElement(audio_adaptation_set, "Representation")
            representation.set("id", str(audio_stream['id']))
            representation.set("codecs", audio_stream['codecs'])
            representation.set("bandwidth", str(audio_stream['bandwidth']))

            base_url = ET.SubElement(representation, "BaseURL")
            # 通过后端代理避免跨域问题
            proxied_audio_url = f"/api/video/proxy?domain=bilibili.com&url=" + requests.utils.quote(audio_stream['baseUrl'], safe='')
            base_url.text = proxied_audio_url

            segment_base = ET.SubElement(representation, "SegmentBase")
            segment_base.set("indexRange", audio_stream['SegmentBase']['indexRange'])
            initialization = ET.SubElement(segment_base, "Initialization")
            initialization.set("range", audio_stream['SegmentBase']['Initialization'])

    mpd_xml_string = ET.tostring(mpd, encoding='unicode')
    
    return Response(content=mpd_xml_string, media_type="application/dash+xml")

