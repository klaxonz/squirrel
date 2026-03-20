import json

from core.database import get_session
from models.message import Message


def create_message(content: dict, trace_id: str | None = None, queue_name: str | None = None, message_type: str | None = None) -> Message:
    with get_session() as session:
        message = Message()
        message.body = json.dumps(content)
        message.trace_id = trace_id
        message.queue_name = queue_name
        message.message_type = message_type
        session.add(message)
        session.commit()
        return message
