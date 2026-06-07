---
title: 'Site-runtimes: 跨站点代码严重重复（proxy、pagination、thumbnail、cookie）'
status: open
severity: high
category: code-smell
location: squirrel-site-runtimes/*/src/*/proxy.py, subscription.py, extractor.py, runtime.py
---

## 问题描述

### 1. Proxy 类重复（4 站点）
JavdbProxy、YouPornProxy、PornhubProxy、YouTubeProxy 的 `handle_m3u8`、`_build_client_params`、`handle_stream` 几乎一致，仅 site slug/domain 不同。~300 行/份。

### 2. 订阅同步分页逻辑重复（3 站点）
YouPorn、Pornhub、Javdb 的 `_resolve_page()`、`_build_page_url()`、`_resolve_next_page()`、`_resolve_count_offset()`、`_count_page_unique_videos()`、`_extract_video_urls()` 几乎完全相同。~200 行/份。

### 3. 辅助函数重复（全部 5 站点）
`_load_local_attr()` 在 5 个 runtime.py 中完全一致。

### 4. 缩略图处理重复（2 站点）
Pornhub 和 YouPorn extractor 的 `_META_THUMBNAIL_PATTERNS`、`_normalize_thumbnail`、`_looks_like_expiring_preview_thumbnail`、`_fetch_page_thumbnail_url` 一致。~80 行/份。

### 5. Cookie header 构建重复
Pornhub 和 YouPorn extractor 的 `_build_cookie_header` 完全一致。

### 其他
- Pornhub 提取器直接使用 `import requests` 而非 SDK 的 `crawl.request`
- Pornhub 订阅 404 时 `self.url = self.url.replace('/videos', '')` 改变实例状态产生副作用
- YouPorn `__init__.py` 延迟 import 模式与其他站点不一致

## 影响

- ~800 行可合并的重复代码
- bug 修复需同步 N 份，易遗漏
- 不一致行为（如 Pornhub 直接使用 requests 绕过限速）

## 建议方向

1. 在 SDK 中抽取 `BaseProxy`，各站点仅重写 site 特定配置
2. 抽取 `BaseHtmlPaginationSubscription`，各站点仅提供 selector 和解析逻辑
3. 将 `_load_local_attr` 移入 SDK 工具函数
4. 将缩略图标准化移入 SDK 共享工具
5. Pornhub 改用 `crawl.request` 而非裸 `requests`
6. Pornhub 订阅 404 回退改用局部变量而非 `self.url` 变异
