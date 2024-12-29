import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict

import feedparser
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response, WebSocket
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select, delete
from sse_starlette.sse import EventSourceResponse

from core.database import get_session
from models.podcast import (
    PodcastChannel,
    PodcastEpisode,
    PodcastSubscription,
    PodcastPlayHistory
)


class PlayProgressUpdate(BaseModel):
    position: int
    duration: int


# 添加请求模型
class PreviewPodcastRequest(BaseModel):
    rss_url: str


class SubscribePodcastRequest(BaseModel):
    rss_url: str


router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])

# 创建内存缓存
progress_cache = defaultdict(dict)
last_write_time = {}

# 存储播放进度的内存缓存
play_progress_connections = {}

# 存储活跃的WebSocket连接
active_connections: Dict[int, WebSocket] = {}


async def write_progress_to_db(episode_id: int, session: Session):
    """后台任务：将缓存中的进度写入数据库"""
    if episode_id not in progress_cache:
        return

    progress_data = progress_cache[episode_id]
    history = session.exec(
        select(PodcastPlayHistory)
        .where(PodcastPlayHistory.episode_id == episode_id)
    ).first()

    if not history:
        history = PodcastPlayHistory(
            episode_id=episode_id,
            **progress_data
        )
    else:
        for key, value in progress_data.items():
            setattr(history, key, value)

    session.add(history)
    session.commit()

    # 清理缓存
    del progress_cache[episode_id]
    del last_write_time[episode_id]


async def send_progress_updates(episode_id: int) -> AsyncGenerator[str, None]:
    """生成进度更新事件"""
    try:
        while True:
            if episode_id in progress_cache:
                data = progress_cache[episode_id]
                yield {
                    "event": "progress",
                    "data": data
                }
            await asyncio.sleep(1)  # 每秒检查一次进度
    except asyncio.CancelledError:
        # 清理连接
        if episode_id in play_progress_connections:
            del play_progress_connections[episode_id]


@router.post("/episodes/{episode_id}/play")
async def update_play_progress(
        episode_id: int,
        progress: PlayProgressUpdate,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_session)
):
    progress_cache[episode_id].update({
        "position": progress.position,
        "duration": progress.duration,
        "last_played_at": datetime.now(),
        "is_finished": progress.position >= progress.duration * 0.9
    })

    # 检查是否需要写入数据库
    now = datetime.now()
    last_write = last_write_time.get(episode_id)

    should_write = (
            not last_write or  # 首次写入
            (now - last_write) > timedelta(minutes=1) or  # 距离上次写入超过1分钟
            progress.position >= progress.duration * 0.9  # 播放接近结束
    )

    if should_write:
        background_tasks.add_task(write_progress_to_db, episode_id, session)
        last_write_time[episode_id] = now

    return {"message": "进度已更新"}


# 添加定时清理任务
async def cleanup_expired_cache():
    while True:
        now = datetime.now()
        expired_episodes = [
            episode_id
            for episode_id, last_write in last_write_time.items()
            if (now - last_write) > timedelta(hours=1)
        ]

        for episode_id in expired_episodes:
            if episode_id in progress_cache:
                del progress_cache[episode_id]
            del last_write_time[episode_id]

        await asyncio.sleep(3600)  # 每小时检查一次


@router.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(cleanup_expired_cache())


@router.post("/channels/subscribe")
async def subscribe_podcast(
        request: SubscribePodcastRequest,
        session: Session = Depends(get_session)
):
    """订阅新的播客"""
    # 检查是否已订阅
    existing = session.exec(
        select(PodcastChannel).where(PodcastChannel.rss_url == request.rss_url)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="已订阅该播客")

    feed = feedparser.parse(request.rss_url)
    if hasattr(feed, 'bozo_exception'):
        raise HTTPException(status_code=400, detail="无效的RSS地址")

    description = feed.feed.description if hasattr(feed.feed, "description") else None
    if description:
        description = re.sub(r'<.*?>', '', description)

    title = feed.feed.title
    author = feed.feed.author if hasattr(feed.feed, "author") else None
    cover_url = feed.feed.image.href if hasattr(feed.feed, "image") else None
    website_url = feed.feed.link if hasattr(feed.feed, "link") else None
    language = feed.feed.language if hasattr(feed.feed, "language") else None

    # 创建频道
    channel = PodcastChannel(
        title=title,
        description=description,
        author=author,
        cover_url=cover_url,
        rss_url=request.rss_url,
        website_url=website_url,
        language=language,
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
            func.count(PodcastEpisode.id).label('total_count')
        )
        .join(PodcastSubscription)
        .outerjoin(PodcastEpisode)  # 使用 outerjoin 以包含没有剧集的频道
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
    result = []
    for channel, total_count in channels_with_count:
        # 获取最新剧集
        latest_episode = session.exec(
            select(PodcastEpisode)
            .where(PodcastEpisode.channel_id == channel.id)
            .where(PodcastEpisode.audio_url is not None)  # 确保有音频地址
            .order_by(PodcastEpisode.published_at.desc())
            .limit(1)
        ).first()

        if latest_episode:
            episode_dict = latest_episode.dict()
            # 确保音频 URL 是完整的
            if not episode_dict['audio_url'].startswith(('http://', 'https://')):
                episode_dict['audio_url'] = f"https://{episode_dict['audio_url']}"
            episodes = [episode_dict]
        else:
            episodes = []

        channel_dict = channel.dict()
        channel_dict.update({
            'total_count': total_count,
            'episodes': episodes,
            'last_updated': latest_episode.published_at if latest_episode else channel.last_updated
        })
        result.append(channel_dict)

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > page * page_size
    }


@router.get("/channels/{channel_id}/episodes")
async def get_channel_episodes(
        channel_id: int,
        page: int = 1,
        page_size: int = 20,
        sort_order: str = "desc",
        session: Session = Depends(get_session)
):
    """获取频道的剧集列表"""
    # 确定排序方式
    order_by = PodcastEpisode.published_at.desc() if sort_order == "desc" else PodcastEpisode.published_at.asc()

    # 查询剧集
    episodes = session.exec(
        select(PodcastEpisode)
        .where(PodcastEpisode.channel_id == channel_id)
        .order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    # 获取总数
    total = session.exec(
        select(func.count(PodcastEpisode.id))
        .where(PodcastEpisode.channel_id == channel_id)
    ).one()

    return {
        "items": [episode.dict() for episode in episodes],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > page * page_size
    }


@router.get("/episodes/{episode_id}/progress")
async def stream_progress(
        episode_id: int,
        response: Response,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_session)
):
    """建立 SSE 连接以流式传输进度更新"""
    play_progress_connections[episode_id] = True

    return EventSourceResponse(
        send_progress_updates(episode_id),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/episodes/{episode_id}/progress")
async def update_progress(
        episode_id: int,
        progress: PlayProgressUpdate,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_session)
):
    """更新播放进度（只更新缓存）"""
    progress_cache[episode_id].update({
        "position": progress.position,
        "duration": progress.duration,
        "last_played_at": datetime.now(),
        "is_finished": progress.position >= progress.duration * 0.9
    })

    # 检查是否需要写入数据库
    now = datetime.now()
    last_write = last_write_time.get(episode_id)

    should_write = (
            not last_write or  # 首次写入
            (now - last_write) > timedelta(minutes=1) or  # 距离上次写入超过1分钟
            progress.position >= progress.duration * 0.9  # 播放接近结束
    )

    if should_write:
        background_tasks.add_task(write_progress_to_db, episode_id, session)
        last_write_time[episode_id] = now

    return {"message": "进度已更新"}


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
    """获取已订阅的频道的最新剧集"""
    # 先获取已订阅的频道ID
    subscribed_channels = session.exec(
        select(PodcastSubscription.channel_id)
    ).all()

    if not subscribed_channels:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "has_more": False
        }

    # 查询这些频道的最新剧集
    episodes_stmt = (
        select(PodcastEpisode)
        .where(PodcastEpisode.channel_id.in_(subscribed_channels))
        .order_by(PodcastEpisode.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    episodes = session.exec(episodes_stmt).all()

    if not episodes:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "has_more": False
        }

    # 获取相关的频道信息
    channel_ids = {e.channel_id for e in episodes}
    channels_stmt = (
        select(PodcastChannel)
        .where(PodcastChannel.id.in_(channel_ids))
    )
    channels = {c.id: c for c in session.exec(channels_stmt).all()}

    # 获取总数
    total = session.exec(
        select(func.count(PodcastEpisode.id))
        .where(PodcastEpisode.channel_id.in_(subscribed_channels))
    ).one()

    # 组装结果
    result = []
    for episode in episodes:
        channel = channels[episode.channel_id]
        episode_dict = episode.dict()
        episode_dict['channel_title'] = channel.title
        episode_dict['channel_cover_url'] = channel.cover_url
        result.append(episode_dict)

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > page * page_size
    }


@router.post("/channels/preview")
async def preview_podcast(
        request: PreviewPodcastRequest,
        session: Session = Depends(get_session)
):
    """预览播客信息"""
    # 解析RSS feed
    feed = feedparser.parse(request.rss_url)
    if hasattr(feed, 'bozo_exception'):
        raise HTTPException(status_code=400, detail="无效的RSS地址")

    # 提取预览信息
    description = feed.feed.description if hasattr(feed.feed, "description") else None
    if description:
        description = re.sub(r'<.*?>', '', description)

    return {
        "code": 0,
        "data": {
            "title": feed.feed.title,
            "description": description,
            "author": feed.feed.author if hasattr(feed.feed, "author") else None,
            "cover_url": feed.feed.image.href if hasattr(feed.feed, "image") else None,
            "website_url": feed.feed.link if hasattr(feed.feed, "link") else None,
            "language": feed.feed.language if hasattr(feed.feed, "language") else None,
        }
    }


@router.get("/listening")
async def get_listening_podcasts(
        session: Session = Depends(get_session)
):
    """获取正在收听的播客"""
    stmt = (
        select(PodcastChannel)
        .join(PodcastChannel.episodes)
        .join(PodcastEpisode.play_history)
        .where(PodcastPlayHistory.is_finished is False)
        .order_by(PodcastPlayHistory.last_played_at.desc())
        .limit(6)
    )

    channels = session.exec(stmt).all()

    return [
        {
            **channel.dict(),
            "current_episode": channel.episodes[0].dict(),
            "progress": channel.episodes[0].play_history[0].position / channel.episodes[0].play_history[0].duration
            if channel.episodes[0].play_history[0].duration > 0 else 0
        }
        for channel in channels
    ]


@router.get("/categories")
async def get_podcast_categories():
    """获取播客分类列表"""
    return {
        "categories": [
            {"label": "全部", "value": "all"},
            {"label": "新闻", "value": "news"},
            {"label": "科技", "value": "tech"},
            {"label": "商业", "value": "business"},
            {"label": "文化", "value": "culture"},
            {"label": "教育", "value": "education"},
            {"label": "娱乐", "value": "entertainment"},
            {"label": "音乐", "value": "music"},
            {"label": "其他", "value": "others"}
        ]
    }


@router.websocket("/episodes/{episode_id}/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        episode_id: int,
        session: Session = Depends(get_session)
):
    await websocket.accept()
    active_connections[episode_id] = websocket

    try:
        while True:
            # 等待客户端发送进度更新
            data = await websocket.receive_json()

            # 更新缓存
            progress_cache[episode_id].update({
                "position": data["position"],
                "duration": data["duration"],
                "last_played_at": datetime.now(),
                "is_finished": data["position"] >= data["duration"] * 0.9
            })

            # 检查是否需要写入数据库
            now = datetime.now()
            last_write = last_write_time.get(episode_id)

            should_write = (
                    not last_write or  # 首次写入
                    (now - last_write) > timedelta(minutes=1) or  # 距离上次写入超过1分钟
                    data["position"] >= data["duration"] * 0.9  # 播放接近结束
            )

            if should_write:
                await write_progress_to_db(episode_id, session)
                last_write_time[episode_id] = now

    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        if episode_id in active_connections:
            del active_connections[episode_id]
