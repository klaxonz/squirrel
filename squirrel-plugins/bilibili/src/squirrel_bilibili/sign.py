from __future__ import annotations

import time
import urllib.parse
from functools import reduce
from hashlib import md5
from typing import Dict

from crawl import request

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]


def enc_wbi(params: Dict[str, str], img_key: str, sub_key: str) -> Dict[str, str]:
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params = dict(params)
    params['wts'] = str(curr_time)
    params = dict(sorted(params.items()))
    params = {k: ''.join(ch for ch in str(v) if ch not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params


def get_wbi_keys() -> tuple[str, str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.bilibili.com/'
    }
    resp = request('GET', 'https://api.bilibili.com/x/web-interface/nav', headers=headers, timeout=15)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


def sign(params: Dict[str, str]) -> str:
    img_key, sub_key = get_wbi_keys()
    signed_params = enc_wbi(params, img_key, sub_key)
    return urllib.parse.urlencode(signed_params)


