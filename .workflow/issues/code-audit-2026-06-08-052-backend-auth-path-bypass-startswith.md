---
title: Auth 中间件路径匹配使用 startswith 可被绕过
status: fixed
fixed_by: 将 is_public_api_path 的 startswith 匹配改为精确匹配 + 带分隔符前缀匹配
severity: medium
category: security
location: squirrel-backend/routes/middleware/auth.py:25-30
---

## 问题描述

`is_public_api_path()` 使用 `str.startswith()` 检查公开路径，导致前缀误匹配。例如 `/api/users/login_malicious` 匹配 `/api/users/login` 前缀被当作公开路径，`/health/readyanything` 匹配 `/health/ready`。

与 `/api/sites/*/icon` 通配符路径（正确实现）对比，`/api/video/thumbnail` 也会匹配到 `/api/video/thumbnail-admin` 等意外路径。

## 影响

- 保护路径可能被意外暴露为公开
- 新增公开端点时容易误配

## 建议方向

1. 对静态路径使用精确匹配
2. 确保路径分隔符被尊重——比较时附带尾部 `/`
3. 参数化路径使用 URL 模式匹配（如 regex）而非 `startswith`
