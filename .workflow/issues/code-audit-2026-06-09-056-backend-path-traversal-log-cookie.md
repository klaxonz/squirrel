---
title: Backend Path Traversal — Log/Cookie/Icon 文件读取可被绕过
status: open
severity: critical
category: security
location: squirrel-backend/services/log_service.py:51; squirrel-backend/core/cookie_config.py:30-32; squirrel-backend/utils/site_icons.py:26-39
---

## 问题描述

三个位置通过用户输入拼接文件路径，对路径遍历（`../`）缺乏充分校验：

1. **`log_service.py:51`** — `filename` 查询参数直接传入 `os.path.join(LOG_DIR, filename)`，无任何校验。攻击者可传入 `../../etc/passwd` 读取任意文件。

2. **`cookie_config.py:30-32`** — `get_site_cookies_file_path(site_slug)` 仅做 `.strip().lower()`，不阻止 `../`。`site_name` 路径参数来自 HTTP 请求 (`routes/site_cookies.py:26`)。

3. **`site_icons.py:26-39`** — `resolve_site_icon_path(site_name)` 使用 `normalize_site_slug` 但该函数不做路径遍历防护。虽然后续枚举固定文件名，`FileResponse` 返回时仍存在理论风险。

## 影响

已认证用户可通过构造路径读取服务器上任意进程可读文件。Cookie 路径可能被用于写操作越界。

## 建议方向

对所有用户输入的路径部分，使用 `Path.resolve()` 后验证结果仍在允许目录内：
```python
resolved = (LOG_DIR / filename).resolve()
if not resolved.is_relative_to(LOG_DIR.resolve()):
    raiseHTTPException(403, "Invalid path")
```
slug 字段额外过滤 `..`、`/`、`\`。