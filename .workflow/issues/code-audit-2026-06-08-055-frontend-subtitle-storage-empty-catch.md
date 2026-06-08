---
title: usePlayer.ts 空 catch {} 静默丢弃 localStorage 错误
status: fixed
fixed_by: usePlayer.ts:161
severity: low
category: error-handling
location: squirrel-frontend/src/components/video-player/runtime/usePlayer.ts:161
---

## 问题描述

`saveSubtitleStyleToStorage()` 使用 `catch {}`（空 catch 块）包裹 `localStorage.setItem()`。存储配额满或 localStorage 被禁用时，字幕样式偏好静默丢失，无任何反馈。

这是前端中唯一发现的空 catch 块。

## 建议方向

改为 `catch (err) { console.warn('[SPPlayer] Failed to save subtitle style', err) }` 保持静默安全的同時提供可观测性。
