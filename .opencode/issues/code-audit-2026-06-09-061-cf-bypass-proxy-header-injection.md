---
title: CF-Bypass SSRF 增强 — x-proxy 头注入可做 MITM 中间人
status: open
severity: high
category: security
location: squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/service.py:20-22,50-54
---

## 问题描述

这是对 #001（CF-Bypass SSRF 无认证）的补充发现。

`service.py:20-22` 和 `50-54` 中，`x-proxy` 请求头被直接信任并作为代理 URL 传递给 `AsyncSession`，不做任何校验。攻击者可设置恶意代理地址（如 SOCKS5），将所有出站流量路由到自己控制的服务器，实现 MITM。

同时，`/{path:path}` mirror 路由（行 51-52）和 `/html` 路由均无主机白名单校验，攻击者可通过 `x-hostname` 头访问内部服务或云元数据端点（`169.254.169.254`）。

## 影响

与 #001 组合：攻击者可 (1) 通过服务访问任意内部网络 (2) 通过指定代理劫持所有流量 (3) 绕过 Cloudflare 保护。

## 建议方向

- 添加认证中间件（API Key 或 JWT）
- 对 `x-proxy` 添加 URL 域名白名单校验
- 对 `x-hostname` 添加内部 IP 段拒绝（`10.x`、`172.16-31.x`、`192.168.x`、`169.254.x`、`127.x`）
- 添加 CORS 策略限制跨域访问