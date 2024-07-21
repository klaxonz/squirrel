import logging

from fastapi import Query, APIRouter
from pydantic import BaseModel

from common.database import get_session
from model.channel import ChannelVideo
from service import download_service
import common.response as response

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道视频接口']
)


@router.get("/api/channel-video/list")
def subscribe_channel(
        channel_name: str = Query(None, description="频道名称"),
        title: str = Query(None, description="视频标题"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    with get_session() as s:
        base_query = s.query(ChannelVideo).filter(ChannelVideo.title != '', ChannelVideo.if_read == 0)
        if channel_name:
            base_query = base_query.filter(ChannelVideo.channel_name.ilike(f'%{channel_name}%'))
        if title:
            base_query = base_query.filter(ChannelVideo.title.ilike(f'%{title}%'))
        total = base_query.count()

        offset = (page - 1) * page_size
        channel_videos = (base_query
                          .order_by(ChannelVideo.uploaded_at.desc())
                          .offset(offset)
                          .limit(page_size))

        channel_video_convert_list = [
            {
                'id': chanel_video.id,
                'channel_id': chanel_video.channel_id,
                'channel_name': chanel_video.channel_name,
                'channel_avatar': chanel_video.channel_avatar,
                'video_id': chanel_video.video_id,
                'title': chanel_video.title,
                'domain': chanel_video.domain,
                'url': chanel_video.url,
                'thumbnail': chanel_video.thumbnail,
                'if_downloaded': chanel_video.if_downloaded,
                'if_read': chanel_video.if_read,
                'uploaded_at': chanel_video.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_at': chanel_video.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for chanel_video in channel_videos
        ]

        channel_video_page = {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_video_convert_list
        }

    return response.success(channel_video_page)


class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/mark-read")
def subscribe_channel(req: MarkReadRequest):
    with get_session() as s:
        s.query(ChannelVideo).where(ChannelVideo.channel_id == req.channel_id,
                                    ChannelVideo.video_id == req.video_id).update({
            'if_read': True
        })

    return response.success()


class DownloadChannelVideoRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/download")
def download_channel_video(req: DownloadChannelVideoRequest):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).filter(ChannelVideo.channel_id == req.channel_id,
                                                     ChannelVideo.video_id == req.video_id).first()

        download_service.start_download(channel_video.url)

        s.query(ChannelVideo).where(ChannelVideo.channel_id == req.channel_id,
                                    ChannelVideo.video_id == req.video_id).update({
            'if_downloaded': True
        })
        s.commit()

    return response.success()
