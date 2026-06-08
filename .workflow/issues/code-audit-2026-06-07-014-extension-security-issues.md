---
title: 'Extension: 多个安全问题 — 超范围权限、凭证存储不当、无传输安全'
status: open
severity: high
category: security
location: squirrel-extension/manifest.json:15,32-34, background.js:36-41, options.js:163-166
---

## 问题描述

### 1. host_permissions 配置为 *://*/*
`manifest.json:15` 声明 `"*://*/*"`，允许扩展在所有网站上读写数据。超出实际需求（仅需 bilibili/youtube/pornhub/javdb），Chrome Web Store 审查会重点关注。

### 2. CSP 中 wasm-unsafe-eval
`manifest.json:32-34` 包含 `'wasm-unsafe-eval'`，但扩展中无任何 WASM 代码。多余的安全放宽。Service worker 也未被 CSP 覆盖。

### 3. 认证 token 存储在 chrome.storage.sync
`background.js:36-41,138` 使用 `chrome.storage.sync` 存储 JWT token。sync 存储会在用户多设备间同步且明文存储，其他拥有 `storage` 权限的扩展可读取。

### 4. 登录凭证通过 HTTP 明文传输
`options.js:163-166` 通过 HTTP POST 发送 email/password。后端默认 `http://localhost:8000`（无加密），用户可配置任意 HTTP endpoint。

## 影响

- Chrome Web Store 可能拒绝上架
- Token 泄露到其他设备和扩展
- 凭证可被中间人截获

## 建议方向

1. host_permissions → 精确到支持的网站列表
2. CSP → 移除 `'wasm-unsafe-eval'`
3. 认证 token → 使用 `chrome.storage.local`（或更安全的 `storage.session`）
4. 传输安全 → 验证 backend host 使用 `https://` 或至少显示警告
5. 抽取通用 `apiRequest()` helper 消除 background.js 中的重复 handler
6. addEventListener 使用 innerHTML 构造 HTML 改为 createElement + textContent
