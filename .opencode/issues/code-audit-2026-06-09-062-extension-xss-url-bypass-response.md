---
title: Extension 安全问题 — XSS innerHTML + URL 匹配绕过 + handleLogin 无状态检查
status: open
severity: high
category: security
location: squirrel-extension/options.js:47-59; squirrel-extension/utils.js:4-7; squirrel-extension/background.js:122-140
---

## 问题描述

这是对 #014/#023 的补充，发现三个新的具体安全问题：

1. **XSS via innerHTML** (`options.js:47-59`) — `url` 变量直接拼入 HTML 模板 `data-url="${url}"` 和 `<span class="url">${url}</span>`，未经转义。历史记录中的恶意 URL 可执行任意脚本。

2. **URL 匹配绕过** (`utils.js:4-7`) — `isSupportedUrl()` 使用 `url.includes(platform.domain)` 字符串匹配，`https://evil.com?bilibili.com` 可绕过。应使用 URL 解析而非字符串匹配。

3. **handleLogin 跳过状态检查** (`background.js:122-140`) — 与 `handleDownload`/`handleSubscribe` 不同，`handleLogin` 不检查 `response.ok` 或 `response.status`，非 200 响应若返回 `{code: 0}` 会被误判为成功。

## 影响

存储型 XSS 可窃取 extension 权限；URL 绕过可触发不支持的域名行为；登录状态误判可导致认证失败掩盖。

## 建议方向

- `options.js` 使用 `textContent` 替代 `innerHTML`，或用 DOMPurify 清理
- `utils.js` 使用 `new URL(url).hostname.endsWith('.' + platform.domain)` 精确匹配
- `background.js` 添加 `if (!response.ok)` 检查，与其他 handler 保持一致