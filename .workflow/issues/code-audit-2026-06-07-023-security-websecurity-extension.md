---
title: 安全 — desktop webSecurity 禁用 + extension 权限过宽
status: open
severity: critical
category: security
location: squirrel-desktop/src/window.mjs:266, squirrel-extension/manifest.json:15
---

## 问题描述

这些安全问题在首轮审计已报告但未被修复（或修复不完整）：

### 1. Desktop webSecurity: false （已在 #003 中报告）
`window.mjs:266` — `webSecurity: false` 禁用 Electron 的同源策略。虽已有提交 #003 相关修复，但当前代码仍存在。

### 2. Desktop sandbox: false
`window.mjs:262` — 主窗口禁用沙箱，结合 webSecurity: false 扩大了攻击面。

### 3. Extension host_permissions 过宽
`manifest.json:15` — `"*://*/*"` 允许在任何网站注入脚本。应缩小到实际域名（bilibili.com, youtube.com 等）。

### 4. Extension token 明文存储
`background.js:138` — access_token 存入 chrome.storage.sync，跨设备同步增加泄露风险。应使用 storage.session。

## 影响

- desktop: 恶意站点可通过 iframe/script 注入访问本地资源
- extension: Chrome Web Store 审核可能拒绝 `*://*/*` 权限
- token 同步到所有登录设备

## 建议方向

1. Desktop: 移除 webSecurity: false，按需放宽已知 CDN 的 CORS
2. Extension: 精确到具体域名，token 改 storage.local 或 storage.session
