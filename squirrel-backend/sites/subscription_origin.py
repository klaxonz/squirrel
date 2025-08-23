import abc
from typing import List
from sites.meta_origin import SubscriptionMeta


class BaseSubscription(abc.ABC):

    def __init__(self, url: str):
        self.url = url

    @abc.abstractmethod
    def get_subscribe_info(self) -> SubscriptionMeta:
        pass

    @abc.abstractmethod
    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        pass

