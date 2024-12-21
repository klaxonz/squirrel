import abc
from typing import List

from model import Subscription
from model.channel import Channel
from meta.channel import SubscriptionMeta


class BaseSubscription(abc.ABC):
    """Abstract base class for channel subscription implementations"""
    
    def __init__(self, url: str):
        self.url = url
    
    @abc.abstractmethod
    def get_subscribe_info(self) -> SubscriptionMeta:
        """Get channel metadata information"""
        pass
    
    @abc.abstractmethod 
    def get_subscribe_videos(self, subscription: Subscription, update_all: bool) -> List[str]:
        """Get list of video URLs from the channel"""
        pass