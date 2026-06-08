---
title: JWT_SECRET_KEY 随机默认值导致重启后所有会话失效
status: open
severity: critical
category: security
location: squirrel-backend/core/config.py:42
---

## 问题描述

`config.py:42` 中的 `JWT_SECRET_KEY: str = token_urlsafe(32)` 在每次进程启动时生成随机密钥。若未通过环境变量设置，服务重启将使所有已签发的 JWT token 失效——所有用户会话丢失、认证 cookie 过期。

这实际上是上一轮 005 号 issue（'change-me-in-env' 硬编码）的修复引入的回归：原来的问题（可猜测密钥）被解决，但引入了更隐蔽的运行时问题。

## 影响

- 每次后端重启（部署、崩溃恢复、滚动更新）导致全部用户强制登出
- 多实例部署中不同实例签名不同，负载均衡下 token 随机无效
- 开发环境频繁重启使调试流程痛苦

## 建议方向

1. 要求 `JWT_SECRET_KEY` 必须通过环境变量设置，启动时校验并抛出清晰错误
2. 或提供文件持久化机制：首次启动写入 `data/jwt_secret.key`，后续启动读取
3. Docker 部署中应在首次启动时生成并持久化到 volume
