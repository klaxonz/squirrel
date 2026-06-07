---
title: 'Desktop: 主窗口禁用 webSecurity 导致安全防护全关'
severity: critical
category: security
location: squirrel-desktop/src/window.mjs:265
---

## 问题描述

主 BrowserWindow 设置 `webSecurity: false`，禁用了同源策略、CSP 强制执行和 HTTPS 证书验证。

## 影响

Renderer 进程加载的任意页面可发起无约束跨域请求、读取跨域数据、绕过 TLS 保护。若用户导航到恶意页面，可访问本地文件或内部服务。

## 建议方向

移除 `webSecurity: false`，改为在 `session.webRequest` hooks（如 media-headers.mjs）中按需放宽已知媒体 CDN 的 CORS 头。如确需禁用，需记录原因并添加严格 CSP header。
