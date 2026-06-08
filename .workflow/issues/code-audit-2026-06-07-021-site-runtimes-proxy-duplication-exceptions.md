---
title: Site-runtimes proxy handle_stream 三站重复 + 异常使用不当
status: fixed
fixed_by: multiple files
severity: high
category: architecture
location: squirrel-site-runtimes/src/
---

## 问题描述

### 1. Proxy handle_stream 复制粘贴
pornhub/proxy.py:69-131、javdb/proxy.py:112-172、youporn/proxy.py:70-130 三个文件的 `handle_stream` 方法几乎完全相同（~60行×3 = 180 行重复）：
- 构建 client config
- 解析 URL / 检测 m3u8
- 条件性 m3u8 处理
- 二进制流响应 + 响应头转发

已有 BaseSiteProxy 提供 `_build_client_params` 和 `handle_m3u8`，但编排逻辑仍在各子类重复。

### 2. 通用 Exception 代替 ParseError
- `javdb/subscription.py:35` — `raise Exception(...)` 应为 `raise ParseError(...)`
- `pornhub/subscription.py:58,73` — 同上

### 3. RateLimitError 从未被抛出
AGENTS.md 规定了 4 种领域异常，`RateLimitError` 是其中之一，但全项目 0 处 raise。限流场景要么静默处理，要么降级为 NetworkError/ParseError，丢失语义。

### 4. 63 处 hardcoded URL + 31 处硬编码 User-Agent

### 5. auth.py 五站结构重复
5 个站点的 check_*_login_status 函数共享相同 5 步模式（读 cookie → 构建请求 → HTTP 请求 → 检查状态码 → 解析响应），无共享基函数。

## 影响

- 站点 HTML 结构变更需改多处
- 异常分类不准确导致上层错误处理错乱
- 新站点接入需复制粘贴大量模板代码

## 建议方向

1. 将 proxy handle_stream 编排逻辑提升到 BaseSiteProxy
2. 所有 3 处通用 Exception 改为 ParseError
3. 在限流路径中加入 raise RateLimitError
4. 抽取 auth base 函数处理 5 站公共流程
5. 统一管理 User-Agent 和 URL 常量

## 修复内容

1. **移除 handle_stream 死代码**: 删除 4 站 proxy 中 handle_stream 方法 + Proxy 类 + SDK 中 VideoProxy/BaseSiteProxy，保留模块级 build_runtime_proxy_config/rewrite_proxy_playlist
2. **Exception→ParseError**: javdb/subscription.py:35, pornhub/subscription.py:58,73
3. **RateLimitError**: 5 站 extractor 增加 rate-limit 关键字检测（too many requests/rate limit/429）
4. **硬编码 URL/UA**: auth 重构中一并清理，proxy 中 UA 合并为单个 import
5. **auth 五站抽取**: 创建 crawl/auth_base.py:check_login_status 共享函数，5 站 auth.py 精简 40-60%
