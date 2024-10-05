from pydantic import BaseModel

class DownloadRequest(BaseModel):
    url: str

class DownloadChangeStateRequest(BaseModel):
    task_id: int