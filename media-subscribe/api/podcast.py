import re

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func
from sqlmodel import Session, select, delete
from typing import List, Optional
from datetime import datetime
import feedparser

from core.database import get_session
from model.podcast import (
    PodcastChannel,
    PodcastEpisode,
    PodcastSubscription
)

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


@router.post("/channels/subscribe")
async def subscribe_podcast(
        rss_url: str,
        session: Session = Depends(get_session)
):
    """订阅新的播客"""
    # 检查是否已订阅
    existing = session.exec(
        select(PodcastChannel).where(PodcastChannel.rss_url == rss_url)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已订阅该播客")

    # 解析RSS feed
    feed = feedparser.parse(rss_url)
    if hasattr(feed, 'bozo_exception'):
        raise HTTPException(status_code=400, detail="无效的RSS地址")

    # 创建频道
    description = feed.feed.description if hasattr(feed.feed, "description") else None
    if description:
        description = re.sub(r'<.*?>', '', description)
    channel = PodcastChannel(
        title=feed.feed.title,
        description=description,
        author=feed.feed.author if hasattr(feed.feed, "author") else None,
        cover_url=feed.feed.image.href if hasattr(feed.feed, "image") else None,
        rss_url=rss_url,
        website_url=feed.feed.link if hasattr(feed.feed, "link") else None,
        language=feed.feed.language if hasattr(feed.feed, "language") else None,
        last_updated=datetime.now()
    )
    session.add(channel)
    session.flush()

    # 创建订阅关系
    subscription = PodcastSubscription(channel_id=channel.id)
    session.add(subscription)

    def parse_duration(duration_str):
        parts = duration_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        elif len(parts) == 1:
            s = int(parts[0])
            return s
        else:
            return 0

    # 添加剧集
    for entry in feed.entries:
        description = entry.description if hasattr(entry, "description") else None
        if description:
            description = re.sub(r'<.*?>', '', description)
        episode = PodcastEpisode(
            channel_id=channel.id,
            title=entry.title,
            description=description,
            audio_url=entry.enclosures[0].href if hasattr(entry, "enclosures") else None,
            published_at=datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else None,
            duration=parse_duration(entry.itunes_duration) if hasattr(entry, "itunes_duration") else None
        )
        session.add(episode)

    session.commit()
    return {"message": "播客订阅成功"}


@router.get("/channels")
async def get_subscribed_channels(
        page: int = 1,
        page_size: int = 20,
        session: Session = Depends(get_session)
):
    """获取已订阅的播客列表"""
    # 获取频道和对应的剧集数量
    channels_with_count = session.exec(
        select(
            PodcastChannel,
            func.count(PodcastEpisode.id).label('episode_count')
        )
        .join(PodcastSubscription)
        .outerjoin(PodcastEpisode)
        .group_by(PodcastChannel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # 获取总数
    total = session.exec(
        select(func.count(PodcastChannel.id))
        .join(PodcastSubscription)
    ).one()

    # 处理结果
    channels = []
    for channel, episode_count in channels_with_count:
        channel_dict = channel.dict()
        channel_dict['total_count'] = episode_count
        channels.append(channel_dict)

    return {
        "items": channels,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > page * page_size
    }


@router.get("/channels/{channel_id}/episodes", response_model=List[PodcastEpisode])
async def get_channel_episodes(
        channel_id: int,
        page: int = 1,
        page_size: int = 20,
        read_status: Optional[bool] = None,
        session: Session = Depends(get_session)
):
    """获取播客剧集列表"""
    query = select(PodcastEpisode).where(PodcastEpisode.channel_id == channel_id)

    if read_status is not None:
        query = query.where(PodcastEpisode.is_read == read_status)

    episodes = session.exec(
        query.order_by(PodcastEpisode.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return episodes


@router.post("/episodes/{episode_id}/progress")
async def update_episode_progress(
        episode_id: int,
        position: int,
        session: Session = Depends(get_session)
):
    """更新播放进度"""
    episode = session.get(PodcastEpisode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    episode.last_position = position
    session.add(episode)
    session.commit()
    return {"message": "进度更新成功"}


@router.post("/episodes/{episode_id}/mark-read")
async def mark_episode_read(
        episode_id: int,
        is_read: bool,
        session: Session = Depends(get_session)
):
    """标记剧集已读/未读状态"""
    episode = session.get(PodcastEpisode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    episode.is_read = is_read
    session.add(episode)
    session.commit()
    return {"message": "状态更新成功"}


@router.get("/channels/{channel_id}")
async def get_channel_detail(
    channel_id: int,
    session: Session = Depends(get_session)
):
    """获取播客频道详情"""
    channel = session.get(PodcastChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="播客不存在")
        
    # 检查是否已订阅
    subscription = session.exec(
        select(PodcastSubscription)
        .where(PodcastSubscription.channel_id == channel_id)
    ).first()

    # 获取总剧集数量
    total_count = session.exec(
        select(func.count(PodcastEpisode.id))
        .where(PodcastEpisode.channel_id == channel_id)
    ).one()
    
    return {
        **channel.dict(),
        "is_subscribed": subscription is not None,
        "total_count": total_count
    }


@router.post("/channels/{channel_id}/subscribe")
async def toggle_subscription(
    channel_id: int,
    subscribed: bool,
    session: Session = Depends(get_session)
):
    """订阅或取消订阅播客"""
    channel = session.get(PodcastChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="播客不存在")
        
    subscription = session.exec(
        select(PodcastSubscription)
        .where(PodcastSubscription.channel_id == channel_id)
    ).first()
    
    if subscribed and not subscription:
        # 添加订阅
        subscription = PodcastSubscription(channel_id=channel_id)
        session.add(subscription)
        message = "订阅成功"
    elif not subscribed and subscription:
        # 取消订阅
        session.delete(subscription)
        message = "已取消订阅"
    else:
        # 状态未改变
        message = "订阅状态未改变"
        
    session.commit()
    return {"message": message}


@router.delete("/channels/{channel_id}/subscription")
async def unsubscribe_podcast(
    channel_id: int,
    session: Session = Depends(get_session)
):
    """取消订阅播客并删除相关数据"""
    channel = session.get(PodcastChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="播客不存在")
        
    # 删除订阅关系
    subscription = session.exec(
        select(PodcastSubscription)
        .where(PodcastSubscription.channel_id == channel_id)
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="未订阅该播客")
    
    # 删除所有剧集
    session.exec(delete(PodcastEpisode).where(PodcastEpisode.channel_id == channel_id))

    # 删除订阅关系
    session.delete(subscription)
    
    # 删除频道数据
    session.delete(channel)
    
    session.commit()
    
    return {"message": "已取消订阅并清除相关数据"}


@router.get("/episodes/latest")
async def get_latest_episodes(
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session)
):
    """获取所有订阅播客的最新剧集"""
    # 获取已订阅的频道的最新剧集
    episodes = session.exec(
        select(
            PodcastEpisode,
            PodcastChannel.title.label('channel_title'),
            PodcastChannel.cover_url.label('channel_cover_url')
        )
        .join(PodcastChannel)
        .join(PodcastSubscription)
        .order_by(PodcastEpisode.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # 获取总数
    total = session.exec(
        select(func.count(PodcastEpisode.id))
        .join(PodcastChannel)
        .join(PodcastSubscription)
    ).one()

    # 处理结果
    result = []
    for episode, channel_title, channel_cover_url in episodes:
        episode_dict = episode.dict()
        episode_dict['channel_title'] = channel_title
        episode_dict['channel_cover_url'] = channel_cover_url
        result.append(episode_dict)

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > page * page_size
    }
