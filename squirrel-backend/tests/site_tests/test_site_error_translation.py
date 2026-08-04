import pytest

from sites.crawl import AuthError, NetworkError, NotFoundError, ParseError, RateLimitError, SiteError
from sites.squirrel_bilibili import api_client as bilibili_api_client
from sites.squirrel_youtube import ytdlp_support

YOUTUBE_URL = "https://www.youtube.com/watch?v=demo"
BILIBILI_URL = "https://www.bilibili.com/video/BV1xx411c7mD"


# ---------------- YouTube (yt-dlp boundary) ----------------


def _ytdlp_download_error(message: str):
    from yt_dlp.utils import DownloadError

    return DownloadError(message)


def test_ytdlp_private_video_maps_to_auth_error():
    exc = _ytdlp_download_error("Private video. Sign in if you've been granted access to this video.")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, AuthError)
    assert isinstance(translated, SiteError)


def test_ytdlp_login_required_maps_to_auth_error():
    exc = _ytdlp_download_error("Sign in to confirm you're not a bot")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, AuthError)


def test_ytdlp_video_unavailable_maps_to_not_found():
    exc = _ytdlp_download_error("Video unavailable. This video is no longer available because the uploader removed it")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, NotFoundError)


def test_ytdlp_geo_restricted_maps_to_not_found():
    from yt_dlp.utils import GeoRestrictedError

    exc = GeoRestrictedError("This video is not available in your country", countries=["DE"])

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, NotFoundError)


def test_ytdlp_rate_limit_maps_to_rate_limit_error():
    exc = _ytdlp_download_error("HTTP Error 429: Too Many Requests")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, RateLimitError)
    assert translated.retryable is True


def test_ytdlp_network_timeout_maps_to_network_error():
    exc = _ytdlp_download_error("[youtube] demo: Connection timed out")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, NetworkError)
    assert translated.retryable is True


def test_ytdlp_unknown_error_maps_to_parse_error():
    exc = _ytdlp_download_error("Extractor error: unexpected page structure")

    translated = ytdlp_support.translate_ytdlp_error(exc, YOUTUBE_URL)

    assert isinstance(translated, ParseError)


# ---------------- Bilibili (API code + HTTP boundary) ----------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (-404, NotFoundError),
        (-101, AuthError),
        (-403, AuthError),
        (-412, RateLimitError),
        (-400, ParseError),
        (-999, ParseError),
    ],
)
def test_bilibili_api_code_maps_to_typed_error(code, expected):
    with pytest.raises(expected):
        bilibili_api_client._raise_api_code_error(code, "some message", BILIBILI_URL)


def test_bilibili_http_404_maps_to_not_found():
    class _FakeResponse:
        status_code = 404

    class _FakeHttpError(Exception):
        response = _FakeResponse()

    with pytest.raises(NotFoundError):
        bilibili_api_client._translate_http_error(_FakeHttpError("404"), BILIBILI_URL)


def test_bilibili_http_403_maps_to_auth_error():
    class _FakeResponse:
        status_code = 403

    class _FakeHttpError(Exception):
        response = _FakeResponse()

    with pytest.raises(AuthError):
        bilibili_api_client._translate_http_error(_FakeHttpError("403"), BILIBILI_URL)


def test_bilibili_http_429_maps_to_rate_limit_error():
    class _FakeResponse:
        status_code = 429

    class _FakeHttpError(Exception):
        response = _FakeResponse()

    with pytest.raises(RateLimitError):
        bilibili_api_client._translate_http_error(_FakeHttpError("429"), BILIBILI_URL)
