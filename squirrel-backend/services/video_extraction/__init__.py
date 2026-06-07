"""Video extraction service module
Unified management of video extraction logic
"""
from .extractor import _default

extract_video = _default.extract_video
VideoExtractionService = _default.__class__

__all__ = ["extract_video", "VideoExtractionService"]
