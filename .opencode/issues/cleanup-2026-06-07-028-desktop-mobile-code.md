---
title: 桌面端不支持移动端，清理相关代码
status: fixed
fixed_by: multiple files (see design doc)
severity: medium
category: cleanup
location: squirrel-frontend/src/
created: 2026-06-07
---

# Issue：桌面端不支持移动端，清理相关代码

## 描述

本项目桌面端（Electron）明确不支持移动端，但前端（`squirrel-frontend`）中存在大量移动端相关代码，包括：

1. **移动端检测** — `src/composables/useMobile.ts`（768px 断点检测 `isMobile`）
2. **移动端底部导航栏** — `MobileNavigation.vue`、`MobileNav.vue`，以及 `sidebar.ts` 中的 `mobileLabel`/`showOnMobile`、`MOBILE_NAV_ITEMS`
3. **移动端手势支持** — `src/components/video-player/runtime/useGestures.ts`（362 行，touch 事件处理）、`mobileControls.js`
4. **移动端 viewport/safe-area** — `index.html` 的 viewport meta、`App.vue` 的 `100dvh`、`VirtualList.vue` 的 `-webkit-overflow-scrolling: touch`、`MobileNav.vue` 的 `safe-area-inset-bottom`
5. **RSS 阅读器移动端 UI** — `useRssReader.ts` 的 `isMobile`、`showMobileReaderSettings`、`RssSources.vue` 的 mobile `<Sheet>` 面板
6. **大量响应式 CSS** — 20+ 组件中的 `@media (max-width: 768px)` / `@media (max-width: 640px)` / `@media (max-width: 767px)` 等移动端断点适配
7. **视频播放器移动端适配** — `base.css` 中 640px/480px 断点的按钮/控件尺寸缩水

> 注意：`squirrel-desktop` 中的 Android User-Agent（`constants.mjs:16`）用于 YouTube 媒体流请求，属于功能必需，不在清理范围内。

## 清理目标

- [ ] 移除 `useMobile.ts` composable 及其所有引用
- [ ] 移除 `MobileNavigation.vue`、`MobileNav.vue`
- [ ] 移除 `sidebar.ts` 中的 `mobileLabel`、`showOnMobile`、`MOBILE_NAV_ITEMS`
- [ ] 移除 `useGestures.ts` 和 `mobileControls.js`（或确认播放器是否需要保留触摸支持）
- [ ] 清理 `index.html` 的 viewport meta 和 `App.vue` 的移动端 CSS
- [ ] 清理 RSS 阅读器中的移动端 UI 分支
- [ ] 清理所有组件中 `@media (max-width: ...)` 移动端断点样式

## 优先级

P2

## 备注

- `squirrel-desktop/src/` 中的代码（Android UA、`sec-ch-ua-mobile` header）是功能性的，保留不动。
- 应逐组件清理，避免一次性大重构导致回归。
