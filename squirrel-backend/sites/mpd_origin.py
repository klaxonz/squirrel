from abc import ABC, abstractmethod
from typing import Optional
from models.video import Video


class BaseMpdBuilder(ABC):
    """
    Base class for site-specific MPD builders.
    Subclasses must set class attribute `domain` and implement build_mpd.
    """
    domain: Optional[str] = None

    @abstractmethod
    def build_mpd(self, video: Video) -> str:
        """
        Build MPD XML string for the given video.
        """
        raise NotImplementedError

