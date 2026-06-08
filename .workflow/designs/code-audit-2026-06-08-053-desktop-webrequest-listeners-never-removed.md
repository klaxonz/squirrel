---
title: installDesktopMediaHeaders webRequest 监听器清理方案
status: draft
---

## 根因

`installDesktopMediaHeaders()` 在 `session.defaultSession.webRequest` 上注册了 `onBeforeSendHeaders` 和 `onHeadersReceived` 两个监听器，但从未保存清理函数，导致监听器在应用生命周期内永远无法移除。

## 修复思路

1. **`media-headers.mjs`**: 保存 `onBeforeSendHeaders` / `onHeadersReceived` 返回的移除函数，让 `installDesktopMediaHeaders()` 返回一个清理函数 `() => void`
2. **`main.mjs`**: 接收清理函数，在 `app.on('will-quit')` 时调用进行清理

## 涉及文件

| 文件 | 改动 |
|------|------|
| `squirrel-desktop/src/media-headers.mjs:152-209` | 保存 listener 引用，返回 cleanup 函数 |
| `squirrel-desktop/src/main.mjs:60-78` | 接收 cleanup 函数，注册 will-quit 清理 |

## 潜在风险

- Electron < 28 版本的 webRequest 可能不返回移除函数，但项目使用 Electron ^41.2.0，安全
- 清理函数在 will-quit 时调用，此时 session 可能已不可用 — Electron 保证 will-quit 阶段 session 仍有效
