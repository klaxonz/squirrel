from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field


class TaskListQuery:
    def __init__(
        self,
        page: int = Query(1, ge=1, description='Page number'),
        page_size: int = Query(10, ge=1, le=100, description='Page size'),
        search: str | None = Query(None, description='Search keyword'),
        status: str | None = Query(None, description='Task status'),
        task_type: str | None = Query(None, description='Task type'),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.search = search
        self.status = status
        self.task_type = task_type


class TaskCreateRequest(BaseModel):
    name: str = Field(..., description='Task name', min_length=1, max_length=100)
    task_class: str = Field(..., description='Task class name', min_length=1)
    task_type: str = Field(default='user', description='Task type')
    description: str | None = Field(None, description='Task description')
    interval: int = Field(default=60, ge=1, description='Execution interval value')
    unit: str = Field(default='seconds', description='Time unit', pattern='^(seconds|minutes|hours|days)$')
    start_immediately: bool = Field(default=True, description='Whether to execute immediately')
    max_retries: int = Field(default=3, ge=0, description='Max retry count')
    task_params: dict[str, Any] = Field(default_factory=dict, description='Task parameters')
    is_active: bool = Field(default=True, description='Whether active')


class TaskUpdateRequest(BaseModel):
    name: str | None = Field(None, description='Task name', min_length=1, max_length=100)
    description: str | None = Field(None, description='Task description')
    interval: int | None = Field(None, ge=1, description='Execution interval value')
    unit: str | None = Field(None, description='Time unit', pattern='^(seconds|minutes|hours|days)$')
    start_immediately: bool | None = Field(None, description='Whether to execute immediately')
    max_retries: int | None = Field(None, description='Max retry count')
    task_params: dict[str, Any] | None = Field(None, description='Task parameters')
    is_active: bool | None = Field(None, description='Whether active')
