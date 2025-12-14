"""
Base classes for video extractors.

This module provides base classes for video extractors. New code should prefer
using the Extractor Protocol directly, but these base classes are provided for
convenience.
"""
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .interfaces import ExtractionTask, ExtractionResult, VideoMeta, Extractor
from .plugin_registry import register_extractor

logger = logging.getLogger(__name__)


class VideoExtractorBase(ABC):
    """Base class for video extractors with common functionality.
    
    This class implements the Extractor Protocol and provides common functionality.
    Subclasses should implement _get_video_info() to extract video metadata.
    
    The result data is always VideoMeta.
    """
    
    def __init__(self, site_name: str, supported_domains: List[str]):
        self.site_name = site_name
        self.supported_domains = supported_domains
    
    def validate_url(self, url: str) -> bool:
        """Validate if the URL is supported."""
        return any(domain.lower() in url.lower() for domain in self.supported_domains)
    
    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the URL. Default implementation uses validate_url."""
        return self.validate_url(url)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """Implement the extract method of Extractor Protocol."""
        return self.extract_video_info(task)
    
    def extract_video_info(self, task: ExtractionTask) -> ExtractionResult:
        """Extract video information."""
        try:
            # Get video information
            video_info = self._get_video_info(task.url, task.task_id)
            if not video_info:
                return ExtractionResult(
                    success=False,
                    error="Failed to get video information or invalid video"
                )
            
            # Create VideoMeta directly from dict
            video_meta = VideoMeta(
                title=video_info.get('title', ''),
                url=task.url,
                thumbnail=video_info.get('thumbnail'),
                duration=video_info.get('duration'),
                publish_date=video_info.get('publish_date') or video_info.get('upload_date'),
                extra_data=video_info if video_info else None,
            )

            return ExtractionResult(
                success=True,
                data=video_meta,
            )
            
        except Exception as e:
            logger.error(f"Video extraction failed: {task.url}, error: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                error=f"Video extraction error: {str(e)}"
            )
    
    @abstractmethod
    def _get_video_info(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get video information. Must be implemented by subclasses.
        
        Returns:
            Dict containing video metadata, or None if extraction failed
        """
        pass
    
    
    def _is_playlist(self, video_info: Dict[str, Any]) -> bool:
        """Check if the video info represents a playlist."""
        return video_info.get('_type') == 'playlist'


class YoutubeDLExtractorBase(VideoExtractorBase):
    """Base class for yt-dlp-based video extractors.
    
    Note: This base class does not directly import yt-dlp, but expects
    subclasses to provide concrete implementations.
    """
    
    def _get_video_info(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get video information using yt-dlp. Subclasses must provide concrete implementation."""
        return self._extract_with_ytdlp(url, queue_name)
    
    @abstractmethod 
    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Extract video information using yt-dlp. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Build yt-dlp options. Must be implemented by subclasses."""
        pass
