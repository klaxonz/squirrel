---
title: 'cf-bypass: mirror route 未授权开放代理 / SSRF 向量'
status: open
severity: critical
category: security
location: squirrel-cf-bypass/src/squirrel_cf_bypass/app/api/routes.py:51-52, service.py:253-278
---

## 问题描述

`/{path:path}` catch-all mirror route 接受任意 `x-hostname` header，将任意 HTTP 方法/路径/查询/body 代理到该 host。**无上游 host 白名单**。同时，**所有 endpoint（包括 `/cache/clear` 和 mirror route）无任何认证**，CF_BYPASS_HOST/CF_BYPASS_PORT 等 Settings 类定义后从未被使用。

## 影响

- 攻击者可将 sidecar 当作开放 HTTP 代理扫描内网、攻击内部服务
- 无认证导致 headless browser 可被他人滥用消耗资源
- 配置类存在但无效，误导运维人员

## 建议方向

1. 增加 `CF_BYPASS_ALLOWED_HOSTS` 白名单环境变量，不在白名单的返回 403
2. 增加 `CF_BYPASS_API_KEY` 共享密钥认证（/health 除外）
3. 将 Settings 类接入 create_app()，使环境变量真正生效
4. 抓取 challenge 检测逻辑去重，提取共享 ChallengeDetector
