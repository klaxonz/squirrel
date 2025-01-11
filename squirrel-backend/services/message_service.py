import json

from core.database import get_session
from models.message import Message


def create_message(content: dict) -> Message:
    with get_session() as session:
        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()
        return message
