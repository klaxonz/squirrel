---
title: 'Backend: JWT_SECRET_KEY 硬编码默认值 "change-me-in-env"'
status: fixed
fixed_by: squirrel-backend/core/config.py:42
severity: high
category: security
location: squirrel-backend/core/config.py:41
---

## 问题描述

`core/config.py:41`: `JWT_SECRET_KEY: str = 'change-me-in-env'` 是一个**可猜测的默认密钥**。若部署时未通过环境变量覆盖，攻击者可用此密钥伪造任意 JWT token。

## 影响

攻击者可以伪造任意用户身份的 JWT，越权访问所有 API。此值作为代码级默认值存在于所有部署副本中。

## 建议方向

1. 生成随机默认值（如 `secrets.token_urlsafe(32)`），在首次启动时自动生成
2. 或在启动时检查是否为默认值，打印警告或拒绝启动
3. 在文档和配置模板中强调必须修改
