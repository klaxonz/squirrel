import logging

from fastapi import Query, HTTPException, APIRouter
from pydantic import BaseModel

from model.channel import ChannelVideo
from service import download_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=['频道视频接口']
)


@router.get("/api/channel-video/list")
def subscribe_channel(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    try:
        total = ChannelVideo.select().where(ChannelVideo.title != '', ChannelVideo.if_read == 0).count()
        offset = (page - 1) * page_size
        channel_videos = (ChannelVideo
                          .select()
                          .where(ChannelVideo.title != '', ChannelVideo.if_read == 0)
                          .order_by(ChannelVideo.uploaded_at.desc())
                          .offset(offset)
                          .limit(page_size))

        channel_video_convert_list = [
            {
                'id': chanel_video.id,
                'channel_id': chanel_video.channel_id,
                'channel_name': chanel_video.channel_name,
                'video_id': chanel_video.video_id,
                'title': chanel_video.title,
                'domain': chanel_video.domain,
                'url': chanel_video.url,
                'thumbnail': chanel_video.thumbnail,
                'if_downloaded': chanel_video.if_downloaded,
                'if_read': chanel_video.if_read,
                'uploaded_at': chanel_video.uploaded_at,
                'created_at': chanel_video.created_at
            } for chanel_video in channel_videos
        ]

        return {
            "total": total,
            "page": page,
            "pageSize": page_size,
            "data": channel_video_convert_list
        }

    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


class MarkReadRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/mark-read")
def subscribe_channel(req: MarkReadRequest):
    try:
        ChannelVideo.update(if_read=True).where(
            ChannelVideo.channel_id == req.channel_id, ChannelVideo.video_id == req.video_id).execute()
    except Exception as e:
        logger.error("标记成功", exc_info=True)
        raise HTTPException(status_code=500, detail="标记失败")


class DownloadChannelVideoRequest(BaseModel):
    channel_id: str
    video_id: str


@router.post("/api/channel-video/download")
def download_channel_video(req: DownloadChannelVideoRequest):
    try:
        channel_video = ChannelVideo.select().where(ChannelVideo.channel_id == req.channel_id,
                                                    ChannelVideo.video_id == req.video_id).first()
        download_service.start_download(channel_video.url)
        ChannelVideo.update(if_downloaded=True).where(ChannelVideo.channel_id == req.channel_id,
                                                      ChannelVideo.video_id == req.video_id).execute()
        return {"status": "success", "message": "下载任务已启动"}
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")
