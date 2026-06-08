---
title: installDesktopMediaHeaders 注册的 webRequest 监听器从未移除
status: open
severity: low
category: resource-leak
location: squirrel-desktop/src/media-headers.mjs:152-209
---

## 问题描述

`installDesktopMediaHeaders()` 通过 `session.defaultSession.webRequest.onBeforeSendHeaders` 和 `onHeadersReceived` 注册请求拦截器。两个监听器在应用生命周期内从未被移除，也无法在测试或 session 重建时清理。

## 影响

- 单元测试中难以隔离媒体头行为
- session 重建时可能残留旧监听器
- 阻止 session 被垃圾回收

## 建议方向

`installDesktopMediaHeaders()` 返回清理函数（移除监听器），在 `app.on('will-quit')` 时调用。
