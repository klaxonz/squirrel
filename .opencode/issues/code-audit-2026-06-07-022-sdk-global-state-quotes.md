---
title: SDK 全局可变状态 + backend 双引号违规
status: fixed
fixed_by: squirrel-sdk/src/crawl/http.py:335, squirrel-sdk/src/crawl/utils.py:50, squirrel-backend/utils/runtime_http.py:48, squirrel-backend/pyproject.toml:13
severity: medium
category: code-smell
location: squirrel-sdk/src/crawl/http.py, utils.py; squirrel-backend 多个服务文件
---

## 问题描述

### SDK 全局可变状态
- `http.py` 中 3 个模块级全局变量：`_default_rate_limiter`、`_shared_session`、`_cloudflare_bypass_client`
- `utils.py` 中 2 个：`_cookie_file_resolver`、`_cookie_domain_resolver`
- 每个全局变量有对应的 `configure_*()` setter 函数
- 测试间隔离困难，并发场景可能产生竞态

### SDK 中英文混用
- `http.py` 的 `request()`、`get()`、`post()` 等 public 函数 docstring 为中文，其余模块为英文

### Backend 双引号违规（AGENTS.md 约定单引号）
- `services/video_extraction_center_service.py` — 82 处双引号
- `services/video_list_service.py` — 79 处
- `services/video_list_query_service.py` — 71 处
- `services/video_history_service.py` — 59 处
- `utils/metrics.py` — 48 处
- `services/youtube_oauth_service.py` — 37 处
- `utils/cookie.py` — 26 处

## 影响

- 全局状态使测试不可靠（顺序依赖）
- 双引号/单引号混用降低代码一致性，lint 绕过高亮噪音

## 建议方向

1. SDK: 引入 SdkContext 上下文对象封装全局状态，支持依赖注入
2. SDK: 统一 docstring 为英文
3. Backend: 运行 `ruff check --fix` 启用引用规则批量修正
