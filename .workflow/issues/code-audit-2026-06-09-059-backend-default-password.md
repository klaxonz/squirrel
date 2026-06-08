---
title: Backend 默认数据库密码 — POSTGRES_PASSWORD 默认 postgres
status: open
severity: medium
category: security
location: squirrel-backend/core/config.py:30-31
---

## 问题描述

`config.py:30-31` 中 `POSTGRES_PASSWORD` 默认值为 `"postgres"`。虽然 Pydantic Settings 会从 `.env` 覆盖，但如果 `.env` 缺失或该字段未设置，系统将使用弱密码连接数据库。

对比 `JWT_SECRET_KEY` 已有验证器拒绝空值，但数据库密码缺少类似保护。

另：`COOKIECLOUD_PASSWORD`、`KUGOU_MUSIC_COOKIE` 等敏感配置默认为空字符串，而非报错，导致静默失败。

## 影响

生产环境若未配置 `.env`，数据库使用默认弱密码。CookieCloud 同步等功能静默失败无提示。

## 建议方向

- 为 `POSTGRES_PASSWORD` 添加 Pydantic 验证器，非 dev 环境下拒绝默认值
- 对 `COOKIECLOUD_PASSWORD` 等可选但敏感字段添加启动时日志警告