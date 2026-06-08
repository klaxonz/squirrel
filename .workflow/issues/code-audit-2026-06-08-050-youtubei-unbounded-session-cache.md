---
title: YouTubei SESSION_CACHE 无界增长永不过期
status: open
severity: medium
category: performance
location: squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs:17
---

## 问题描述

`SESSION_CACHE` Map 以 auth 模式为 key 缓存 Innertube 运行时实例。每个实例包含完整 session（player data、format decryption keys 等），`Innertube.create()` 开销大。缓存在 cookie 变更、OAuth 刷新或长期运行后无界增长，无 TTL 或大小限制。

## 影响

- 内存消耗持续增长
- 缓存中的过期 session 可能返回过时的解密信息

## 建议方向

1. 添加 LRU 驱逐策略（最大 3 条目）
2. 或添加 TTL 过期
3. OAuth 状态变更或 cookie 清除时主动清理对应缓存
