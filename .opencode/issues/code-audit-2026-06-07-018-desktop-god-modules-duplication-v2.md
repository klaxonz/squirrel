---
title: Desktop 上帝模块 + 代码重复 v2 — youtubei_core(940行) + 3处YouTube解析重复
status: open
severity: high
category: architecture
location: squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs, src/search/providers/youtube.mjs, src/search/providers/remote-channel.mjs
---

## 问题描述

四个主要问题：

**1. youtubei_core.mjs (940 行)** — 处理 OAuth 会话、Innertube 创建、播放解析、字幕、DASH、poToken，5+ 职责

**2. YouTube 解析逻辑在 3 文件重复** (~300 行重复):
- `src/search/providers/youtube.mjs` — 搜索解析
- `src/search/providers/remote-channel.mjs` — 频道视频解析
- 11 对近乎相同的函数（collectVideoRenderers、findContinuationToken、buildCursor 等）

**3. 缓存管理在 3 provider 重复**:
- `bilibili/index.mjs` / `youtube/index.mjs` / `adult-page.mjs` 各有独立的 Map + isExpired + getCachedPayload

**4. site-login.mjs (756 行)** — 5 个近乎相同的 login check 函数（javdb/pornhub/youporn 等）

## 影响

- YouTube API 变更需改 3 个文件，容易遗漏
- 缓存行为不一致（有的异步文件持久化，有的 fire-and-forget）
- 新 site 接入需复制粘贴整个 login checker

## 建议方向

1. 提取共享 YouTube 解析模块 `youtube-parser.mjs`
2. 创建统一缓存模块 `PlaybackCache` class
3. site-login 改为数据驱动：SITE_LOGIN_PROFILES 扩展 + 通用 checkSiteLogin()
4. 拆分 youtubei_core.mjs 为 oauth.mjs / playback.mjs / captions.mjs / dash.mjs
