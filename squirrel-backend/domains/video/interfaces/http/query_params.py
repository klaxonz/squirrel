from datetime import datetime

from fastapi import Query

from domains.video.interfaces.dto.request.video import (
    ContentType,
    DurationFilter,
    SortBy,
    TimeRange,
    VideoCategory,
    YesNoAll,
)


class VideoListQuery:
    def __init__(
        self,
        query: str = Query(None, description='搜索关键字'),
        subscription_id: int = Query(None, description='订阅ID'),
        category: VideoCategory = Query(VideoCategory.ALL, description='阅读状态: all, read, unread, preview, like'),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description='排序字段'),
        nsfw: YesNoAll = Query(YesNoAll.ALL, description='NSFW 过滤: all|yes|no'),
        special: YesNoAll = Query(YesNoAll.ALL, description='特别关注过滤: all|yes|no'),
        site: str = Query(None, description='站点过滤:例如 youtube、bilibili 等(支持别名)'),
        cursor: str | None = Query(None, description='分页游标(首页不传;翻页传上一页响应的 next_cursor)'),
        page_size: int = Query(20, ge=1, le=100, alias='pageSize', description='每页数量'),
        time_range: TimeRange = Query(TimeRange.ALL, description='时间范围: all|today|week|month|year'),
        duration: DurationFilter = Query(DurationFilter.ALL, description='时长: all|short|medium|long'),
        content_type: ContentType = Query(
            ContentType.ALL,
            description='内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR',
        ),
    ) -> None:
        self.query = query
        self.subscription_id = subscription_id
        self.category = category
        self.sort_by = sort_by
        self.nsfw = nsfw
        self.special = special
        self.site = site
        self.cursor = cursor
        self.page_size = page_size
        self.time_range = time_range
        self.duration = duration
        self.content_type = content_type


class VideoRandomQuery:
    def __init__(
        self,
        category: VideoCategory = Query(VideoCategory.ALL, description='类别:all|read|unread|preview|liked|later'),
        subscription_id: int = Query(None, description='订阅ID'),
        nsfw: YesNoAll = Query(YesNoAll.ALL, description='NSFW 过滤: all|yes|no'),
        site: str = Query(None, description='站点过滤:例如 youtube、bilibili 等(支持别名)'),
        query: str = Query(None, description='搜索关键字'),
        time_range: TimeRange = Query(TimeRange.ALL, description='时间范围: all|today|week|month|year'),
        duration: DurationFilter = Query(DurationFilter.ALL, description='时长: all|short|medium|long'),
        content_type: ContentType = Query(
            ContentType.ALL,
            description='内容类型: all|CHANNEL|PLAYLIST|ACTRESS|MOVIE|TV_SERIES|ACTOR',
        ),
    ) -> None:
        self.category = category
        self.subscription_id = subscription_id
        self.nsfw = nsfw
        self.site = site
        self.query = query
        self.time_range = time_range
        self.duration = duration
        self.content_type = content_type


class VideoHistoryListQuery:
    def __init__(
        self,
        video_id: int = Query(None),
        min_duration: int = Query(None),
        start_date: datetime = Query(None),
        end_date: datetime = Query(None),
        query: str = Query(None, description='搜索关键词'),
        nsfw: str = Query(None, description='NSFW筛选: all/yes/no'),
        site: str = Query(None, description='站点筛选'),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=200),
    ) -> None:
        self.video_id = video_id
        self.min_duration = min_duration
        self.start_date = start_date
        self.end_date = end_date
        self.query = query
        self.nsfw = nsfw
        self.site = site
        self.page = page
        self.page_size = page_size
