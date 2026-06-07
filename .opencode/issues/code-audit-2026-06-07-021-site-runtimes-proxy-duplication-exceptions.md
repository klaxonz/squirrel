---
title: Site-runtimes proxy handle_stream 三站重复 + 异常使用不当
status: open
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
