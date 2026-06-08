---
title: BackendPlayerAdapter 后端不可用时进度重试队列无限增长
status: open
severity: medium
category: error-handling
location: squirrel-frontend/src/components/video-player/core/BackendPlayerAdapter.ts:63-66
---

## 问题描述

`flushPending()` 同步播放进度到后端 API 失败时，将失败项推回 `pendingProgress` 数组（L63-66）。若后端持续不可用（服务器宕机、认证错误），此队列无限增长——每次 `saveProgress` 追加，防抖触发 flush，失败重入队，循环永续。

由于 L22-24 的 `slice(-20)` 截断，较早的进度数据被静默丢弃。

## 影响

- 内存泄漏：队列无限增长
- 数据丢失：较早的进度被截断丢弃
- 用户完全不知道进度同步失败

## 建议方向

1. 为每项添加重试计数，最多 3 次后丢弃并 `playerLogger.warn`
2. 或使用指数退避替代立即重入队
3. 在 `slice(-20)` 前优先丢弃重试次数最多的项
