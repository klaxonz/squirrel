import logging
from typing import Dict, Optional

from core import config

logger = logging.getLogger()


def build_ydl_opts(url: str, queue_name: Optional[str] = None, *, skip_download: bool = True) -> Dict:
    """
    构造通用的 yt-dlp 选项：
    - 安静模式与忽略警告
    - 可选跳过下载，仅提取信息
    - 非 YouTube 站点时，注入 thread 级 cookie 文件（如存在）
    """
    ydl_opts: Dict = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': False,
    }
    if skip_download:
        ydl_opts['skip_download'] = True

    try:
        cookie_file_path = config.get_cookies_file_path_thread(queue_name)
        if cookie_file_path and 'youtube.com' not in url:
            ydl_opts['cookiefile'] = cookie_file_path
    except Exception as e:
        # 不因 cookie 注入失败而阻断流程
        logger.debug(f"Skip injecting cookiefile due to error: {e}")

    return ydl_opts


