from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

import common.response as response
from core.database import get_session
from schemas.channel import SubscribeChannelRequest, ChannelUpdateRequest, ChannelDeleteRequest, ToggleStatusRequest
from services.channel_service import ChannelService

router = APIRouter(tags=['频道接口'])


@router.get("/api/channel/subscription-status")
def get_subscription_status(channel_id: str, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    is_subscribed = channel_service.get_subscription_status(channel_id)
    return response.success({"isSubscribed": is_subscribed})


@router.post("/api/channel/subscribe")
def subscribe_channel(req: SubscribeChannelRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    channel_service.subscribe_channel(req.url)
    return response.success()


@router.post("/api/channel/update")
def update_channel(req: ChannelUpdateRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)

    channel_service.update_channel(req.id, req.dict(exclude_unset=True))
    return response.success()


@router.post("/api/channel/delete")
def delete_channel(req: ChannelDeleteRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    channel_service.delete_channel(req.id)
    return response.success()


@router.get("/api/channel/detail")
def channel_detail(id: int, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    channel_dict = channel_service.get_channel_detail(id)
    if channel_dict:
        return response.success(channel_dict)
    raise HTTPException(status_code=404, detail="Channel not found")


@router.get("/api/channel/list")
def list_channels(
        query: str = Query(None, description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page"),
        session: Session = Depends(get_session)
):
    channel_service = ChannelService(session)
    channel_list, total = channel_service.list_channels(query, page, page_size)
    return response.success({
        "total": total,
        "page": page,
        "pageSize": page_size,
        "data": channel_list
    })


@router.post("/api/channel/toggle-status")
def toggle_channel_status(req: ToggleStatusRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    success = channel_service.toggle_channel_status(req.channel_id, req.if_enable, "if_enable")
    return response.success({"success": success})


@router.post("/api/channel/toggle-auto-download")
def toggle_auto_download(req: ToggleStatusRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    success = channel_service.toggle_channel_status(req.channel_id, req.if_enable, "if_auto_download")
    return response.success({"success": success})


@router.post("/api/channel/toggle-download-all")
def toggle_download_all(req: ToggleStatusRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    success = channel_service.toggle_channel_status(req.channel_id, req.if_enable, "if_download_all")
    return response.success({"success": success})


@router.post("/api/channel/toggle-extract-all")
def toggle_extract_all(req: ToggleStatusRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    success = channel_service.toggle_channel_status(req.channel_id, req.if_enable, "if_extract_all")
    return response.success({"success": success})


@router.post("/api/channel/unsubscribe")
def unsubscribe_channel(req: ChannelDeleteRequest, session: Session = Depends(get_session)):
    channel_service = ChannelService(session)
    success = channel_service.unsubscribe_channel(req.id)
    if success:
        return response.success({"message": "Channel unsubscribed successfully"})
    raise HTTPException(status_code=404, detail="Channel not found")
