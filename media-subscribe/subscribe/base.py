import abc
from typing import List

from model.channel import Channel
from meta.channel import ChannelMeta

class BaseSubscribeChannel(abc.ABC):
    """Abstract base class for channel subscription implementations"""
    
    def __init__(self, url: str):
        self.url = url
    
    @abc.abstractmethod
    def get_channel_info(self) -> ChannelMeta:
        """Get channel metadata information"""
        pass
    
    @abc.abstractmethod 
    def get_channel_videos(self, channel: Channel, update_all: bool) -> List[str]:
        """Get list of video URLs from the channel"""
        pass