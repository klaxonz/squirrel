import json
import logging

from common import constants
from common.database import get_session
from common.message_queue import RedisMessageQueue

from model.message import Message

logger = logging.getLogger(__name__)


def start_extract_and_download(url: str, if_only_extract: bool = True, if_subscribe: bool = False, if_retry: bool = False):

    with get_session() as session:

        content = {
            'url': url,
            'if_retry': if_retry,
            'if_subscribe': if_subscribe,
            'if_only_extract': if_only_extract
        }

        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()

        RedisMessageQueue(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD).enqueue(message)
        session.commit()

