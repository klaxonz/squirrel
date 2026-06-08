---
title: 'Frontend: RSS 阅读器未过滤外部 HTML 导致 XSS 漏洞'
status: open
severity: critical
category: security
location: squirrel-frontend/src/views/RssSources.vue:1113
---

## 问题描述

`v-html="cleanAndDecodeHtml(readingEntry.summary)"` 用于渲染 RSS 摘要内容。`cleanAndDecodeHtml` 仅递归解码 HTML 实体，未过滤 `<script>`、`<iframe>`、事件处理器等危险标签。RSS 摘要来自外部不可信源。

## 影响

恶意 RSS feed 可在用户浏览器中执行任意 JavaScript，窃取 JWT token（localStorage）或执行越权操作。依赖中未安装任何 HTML 消毒库（如 DOMPurify）。

## 建议方向

安装 `dompurify` + `@types/dompurify`，在 `v-html` 前使用 `DOMPurify.sanitize()`。注意 SubtitlesPlugin.ts 中的自定义消毒仅针对字幕格式，不适用于通用 HTML。
