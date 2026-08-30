"""FastAPI dependency providers for the composed video application service."""

from fastapi import Request

from domains.video.application.services.creators.service import CreatorService
from domains.video.application.services.crud import VideoCrudService
from domains.video.application.services.engagement.clip_marker import VideoClipMarkerService
from domains.video.application.services.engagement.interaction import VideoInteractionService
from domains.video.application.services.featured import VideoFeaturedService
from domains.video.application.services.history.service import VideoHistoryService
from domains.video.application.services.listing.service import VideoListService
from domains.video.application.services.random import VideoRandomService


def get_video_crud_service(request: Request) -> VideoCrudService:
    return request.app.state.video_service.crud


def get_video_list_service(request: Request) -> VideoListService:
    return request.app.state.video_service.listing


def get_video_random_service(request: Request) -> VideoRandomService:
    return request.app.state.video_service.random


def get_featured_service(request: Request) -> VideoFeaturedService:
    return request.app.state.video_service.featured


def get_video_history_service(request: Request) -> VideoHistoryService:
    return request.app.state.video_service.history


def get_video_interaction_service(request: Request) -> VideoInteractionService:
    return request.app.state.video_service.interaction


def get_clip_marker_service(request: Request) -> VideoClipMarkerService:
    return request.app.state.video_service.clip_marker


def get_creator_service(request: Request) -> CreatorService:
    return request.app.state.video_service.creators
