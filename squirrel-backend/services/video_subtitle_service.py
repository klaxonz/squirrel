from dataclasses import dataclass
from enum import StrEnum

from crawl import RuntimeErrorCode

from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.ports import get_runtime_gateway
from utils.url_helper import normalize_domain

from . import video_crud_service


class SubtitleFormat(StrEnum):
    SRT = "srt"
    VTT = "vtt"


class SubtitleErrorCode(StrEnum):
    INVALID_FORMAT = "invalid_format"
    VIDEO_NOT_FOUND = "video_not_found"
    PROVIDER_NOT_AVAILABLE = "provider_not_available"
    SUBTITLES_NOT_AVAILABLE = "subtitles_not_available"
    RUNTIME_ERROR = "runtime_error"


class SubtitleServiceError(ValueError):
    def __init__(self, code: SubtitleErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SubtitleFile:
    content: str
    filename: str
    media_type: str


def fetch_video_subtitles(
    video_id: int,
    *,
    lang: str | None = None,
    fmt: str = "srt",
    runtime_gateway: SiteRuntimeGateway | None = None,
) -> SubtitleFile:
    normalized_fmt = fmt.lower()
    if normalized_fmt not in {SubtitleFormat.SRT.value, SubtitleFormat.VTT.value}:
        raise SubtitleServiceError(SubtitleErrorCode.INVALID_FORMAT, "Only srt and vtt formats are supported")

    video = video_crud_service.get_video_by_id(video_id)
    if not video:
        raise SubtitleServiceError(SubtitleErrorCode.VIDEO_NOT_FOUND, "Video not found")

    domain = normalize_domain(video.url) or ""
    gateway = runtime_gateway or get_runtime_gateway()
    result = gateway.invoke(
        "fetch_subtitles",
        domain=domain,
        payload={
            "video_id": video.id,
            "url": video.url,
            "title": getattr(video, "title", None),
            "duration": getattr(video, "duration", None),
            "lang": lang,
            "fmt": normalized_fmt,
        },
    )
    if not result.ok or not isinstance(result.data, dict):
        _raise_subtitle_error(result.error)

    content = str(result.data.get("content") or "")
    filename = str(result.data.get("filename") or "").strip()
    media_type = str(result.data.get("media_type") or "").strip()
    if not filename or not media_type:
        raise SubtitleServiceError(
            SubtitleErrorCode.RUNTIME_ERROR,
            "Subtitles provider returned an invalid response",
        )

    return SubtitleFile(
        content=content,
        filename=filename,
        media_type=media_type,
    )


def _raise_subtitle_error(error) -> None:
    if error is None:
        raise SubtitleServiceError(
            SubtitleErrorCode.PROVIDER_NOT_AVAILABLE,
            "Subtitles provider not available for this domain",
        )

    if error.code == RuntimeErrorCode.ROUTE_NOT_FOUND:
        raise SubtitleServiceError(
            SubtitleErrorCode.PROVIDER_NOT_AVAILABLE,
            "Subtitles provider not available for this domain",
        )
    if error.code == RuntimeErrorCode.SUBTITLES_NOT_AVAILABLE:
        raise SubtitleServiceError(SubtitleErrorCode.SUBTITLES_NOT_AVAILABLE, "No subtitles available")

    message = str(error.message or "").strip()
    raise SubtitleServiceError(
        SubtitleErrorCode.RUNTIME_ERROR,
        message or "Subtitles provider not available for this domain",
    )
