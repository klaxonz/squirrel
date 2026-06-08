---
title: YouPorn 播放缓存键使用二进制标志而非 SHA1 哈希
status: open
severity: high
category: code-smell
location: squirrel-desktop/src/playback/providers/youporn/index.mjs:277
---

## 问题描述

YouPorn 的播放缓存键使用 `cookie=${cookie ? '1' : '0'}`（二进制标志），而所有其他 provider（YouTube、Bilibili、Pornhub）使用 `createHash('sha1').update(cookie).digest('hex').slice(0, 16)` 按实际 cookie 内容做域限定。

这意味着两个不同用户的 YouPorn cookie（如用户 A vs 用户 B）产生相同缓存键，可能返回错误用户的播放数据，或返回匿名会话数据给已认证用户。

## 影响

- 缓存污染：不同用户共享播放数据
- 已认证用户可能拿到匿名限制的低清流
- 隐私问题：用户 B 可能获取用户 A 的缓存数据

## 建议方向

将缓存键改为与其他 provider 一致的 SHA1 cookie 哈希模式。统一抽取为 `shared/playback-cache.mjs` 中的工具函数。
