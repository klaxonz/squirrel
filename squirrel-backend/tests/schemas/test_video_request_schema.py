import sys
from enum import StrEnum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from schemas.video.request.video import ContentType, DurationFilter, SortBy, TimeRange, VideoCategory, YesNoAll


def test_video_filter_enums_are_str_enums():
    assert issubclass(SortBy, StrEnum)
    assert issubclass(VideoCategory, StrEnum)
    assert issubclass(YesNoAll, StrEnum)
    assert issubclass(TimeRange, StrEnum)
    assert issubclass(DurationFilter, StrEnum)
    assert issubclass(ContentType, StrEnum)


def test_video_filter_enum_values_match_query_contract():
    assert SortBy.UPLOADED_AT == "publish_date"
    assert VideoCategory.ALL == "all"
    assert VideoCategory.LIKED == "liked"
    assert YesNoAll.YES == "yes"
    assert TimeRange.MONTH == "month"
    assert DurationFilter.LONG == "long"
    assert ContentType.TV_SERIES == "TV_SERIES"
