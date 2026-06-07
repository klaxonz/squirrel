"""
JavDB video extractor.
"""
import logging
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    VideoExtractorBase,
    VipError,
)

from .html_client import fetch_javdb_html

logger = logging.getLogger(__name__)


def _fetch_video_info(url: str) -> dict[str, Any]:
    response = fetch_javdb_html(url)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    video_info: dict[str, Any] = {}

    vip_keywords = ["永久VIP", "Join VIP"]
    login_keywords = ["欢迎登入", "歡迎登入", "requires login to view"]
    if any(keyword in html for keyword in vip_keywords):
        raise VipError("需要永久VIP权限", context={"url": url, "reason": "vip_required"})
    if any(keyword in html for keyword in login_keywords):
        raise AuthError("需要登录访问", context={"url": url, "reason": "login_required"})

    title_nodes = soup.select(".title strong")
    if not title_nodes:
        raise ParseError("无法解析视频标题，页面结构可能已变化", context={"url": url, "reason": "title_not_found"})
    title_parts = [node.get_text(strip=True) for node in title_nodes if node.get_text(strip=True)]
    video_info["title"] = " ".join(title_parts) if title_parts else None

    thumb_node = soup.select_one(".video-cover")
    if thumb_node and thumb_node.has_attr("src"):
        raw_src = thumb_node["src"]
        if str(raw_src).startswith("http"):
            video_info["thumbnail"] = raw_src
        else:
            from urllib.parse import urljoin

            video_info["thumbnail"] = urljoin(url, raw_src)
    else:
        video_info["thumbnail"] = None

    try:
        duration_node = soup.select_one(".movie-panel-info .panel-block:nth-of-type(3) span")
        if duration_node:
            duration_text = duration_node.get_text(strip=True).split(" ")[0]
            video_info["duration"] = int(duration_text) * 60
        else:
            video_info["duration"] = None
    except (ValueError, TypeError, AttributeError):
        video_info["duration"] = None

    try:
        date_node = soup.select_one(".movie-panel-info .panel-block:nth-of-type(2) span")
        if date_node:
            timestamp = int(datetime.strptime(date_node.get_text(strip=True), "%Y-%m-%d").timestamp())
            video_info["timestamp"] = timestamp
        else:
            video_info["timestamp"] = None
    except (ValueError, TypeError, AttributeError):
        video_info["timestamp"] = None

    return video_info


class JavdbExtractor(VideoExtractorBase):
    """JavDB video extractor."""

    site_name = "javdb"
    supported_domains = ["javdb.com"]
    url_patterns = [
        "javdb.com/v/",
        "javdb.com/video/"
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _get_video_info(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Get JavDB video information."""
        try:
            video_info = _fetch_video_info(url)
            self._process_javdb_info(video_info)
            return video_info

        except (AuthError, VipError, NotFoundError, ParseError, NetworkError, RateLimitError):
            raise
        except Exception as e:  # SDK boundary — translate unexpected errors to domain types
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if "login" in error_msg or "登入" in error_msg or "登录" in error_msg:
                raise AuthError(f"需要登录访问: {url}", context=context)
            elif "vip" in error_msg or "永久vip" in error_msg:
                raise VipError(f"需要VIP权限: {url}", context=context)
            elif "不存在" in error_msg or "404" in error_msg:
                raise NotFoundError(f"视频不存在: {url}", context=context)
            elif any(kw in error_msg for kw in ["timeout", "connection", "网络"]):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            elif any(kw in error_msg for kw in ["too many requests", "rate limit", "429"]):
                raise RateLimitError(f"请求频率过高: {url}", context=context)
            else:
                logger.error("JavDB视频信息提取失败: %s", url, exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _process_javdb_info(self, video_info: dict) -> None:
        """Process JavDB-specific information."""
        try:
            if "timestamp" in video_info:
                if isinstance(video_info["timestamp"], (int, float)):
                    video_info["publish_date"] = datetime.fromtimestamp(video_info["timestamp"])
        except (ValueError, TypeError) as e:
            logger.warning("处理JavDB特定信息失败: %s", e)
