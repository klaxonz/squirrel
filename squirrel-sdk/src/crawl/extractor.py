"""
Base classes for video extractors.

This module provides base classes for video extractors. New code should prefer
using the Extractor Protocol directly, but these base classes are provided for
convenience.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from .core import ExtractionResult, ExtractionTask, VideoMeta
from .exceptions import ErrorCategory, ParseError, PluginError

logger = logging.getLogger(__name__)


class VideoExtractorBase(ABC):
    """Base class for video extractors with common functionality.

    This class implements the Extractor Protocol and provides common functionality.
    Subclasses should implement _get_video_info() to extract video metadata.

    The result data is always VideoMeta.
    """

    url_patterns: list[str] = []

    def __init__(self, site_name: str, supported_domains: list[str]):
        self.site_name = site_name
        self.supported_domains = supported_domains

    def validate_url(self, url: str) -> bool:
        """Validate if the URL is supported."""
        return any(domain.lower() in url.lower() for domain in self.supported_domains)

    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the URL."""
        if not self.validate_url(url):
            return False
        if self.url_patterns:
            return any(p in url.lower() for p in self.url_patterns)
        return True

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """Implement the extract method of Extractor Protocol."""
        return self.extract_video_info(task)

    def extract_video_info(self, task: ExtractionTask) -> ExtractionResult:
        """Extract video information."""
        try:
            video_info = self._get_video_info(task.url, task.task_id)
            if not video_info:
                return ExtractionResult.failure(
                    ParseError("Failed to get video information"),
                    context={"url": task.url}
                )

            video_meta = VideoMeta(
                title=video_info.get("title", ""),
                url=task.url,
                thumbnail=video_info.get("thumbnail"),
                duration=video_info.get("duration"),
                publish_date=video_info.get("publish_date") or video_info.get("upload_date"),
                extra_data=video_info,
            )

            return ExtractionResult.success_result(video_meta)

        except PluginError as e:
            logger.error(
                f"Video extraction failed: {task.url}, category={e.category.value}, error={e.message}",
                exc_info=True,
                extra={"url": task.url, "error_category": e.category.value}
            )
            return ExtractionResult.failure(e, context={"url": task.url})

        except Exception as e:
            logger.error(
                f"Unexpected error during extraction: {task.url}, error={e}",
                exc_info=True,
                extra={"url": task.url}
            )
            return ExtractionResult.failure(
                PluginError(f"Unexpected error: {e}", category=ErrorCategory.UNKNOWN),
                context={"url": task.url, "error_type": type(e).__name__}
            )

    @abstractmethod
    def _get_video_info(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Get video information. Must be implemented by subclasses.

        Returns:
            Dict containing video metadata, or None if extraction failed
        """
        pass

    def _is_playlist(self, video_info: dict[str, Any]) -> bool:
        """Check if the video info represents a playlist."""
        return video_info.get("_type") == "playlist"


class YoutubeDLExtractorBase(VideoExtractorBase):
    """Base class for yt-dlp-based video extractors.

    Note: This base class does not directly import yt-dlp, but expects
    subclasses to provide concrete implementations.
    """

    def _get_video_info(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Get video information using yt-dlp. Subclasses must provide concrete implementation."""
        return self._extract_with_ytdlp(url, queue_name)

    @abstractmethod
    def _extract_with_ytdlp(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Extract video information using yt-dlp. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _build_ytdlp_opts(self, url: str, queue_name: str | None = None) -> dict[str, Any]:
        """Build yt-dlp options. Must be implemented by subclasses."""
        pass
