import re


def extract_id_from_url(url: str) -> str:
    """
    Extract the video id from the given url.
    :param url: The url to extract the video id from.
    :return: The video id.
    """
    if "youtube.com" in url:
        return extract_youtube_id(url)
    elif "bilibili.com" in url:
        return extract_bilibili_id(url)
    elif "pornhub.com" in url:
        return extract_pornhub_id(url)
    else:
        raise ValueError("Invalid url")


def extract_youtube_id(url: str) -> str:
    """
    Extract the video id from the given youtube url.
    :param url: The url to extract the video id from.
    :return: The video id.
    """
    if "youtube.com" in url:
        return url.split("v=")[1]
    else:
        raise ValueError("Invalid url")


def extract_bilibili_id(url: str) -> str:
    """
    Extract the Bilibili video id (BV number) from the given url.
    :param url: The url to extract the Bilibili video id from.
    :return: The Bilibili video id (BV plus alphanumeric characters).
    :raises ValueError: If the url is invalid or does not contain a Bilibili video id.
    """
    pattern = r'BV[0-9A-Za-z]+'
    match = re.search(pattern, url)
    if match:
        return match.group(0)  # 返回完整的BV加上后面的ID
    else:
        raise ValueError("Invalid url")


def extract_pornhub_id(url: str) -> str:
    pattern = r"viewkey=([^&]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid url")
