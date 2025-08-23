from abc import ABC, abstractmethod
from typing import Optional, Tuple
from models.video import Video


class BaseSubtitlesProvider(ABC):
    """
    Base class for site-specific subtitles providers.
    Subclasses must set class attribute `domain` and implement get_subtitles.
    """
    domain: Optional[str] = None

    @abstractmethod
    def get_subtitles(self, video: Video, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        """
        Fetch subtitles for a given video and return a tuple of
        (srt_text, suggested_filename). The `fmt` currently supports only 'srt'.
        """
        raise NotImplementedError

