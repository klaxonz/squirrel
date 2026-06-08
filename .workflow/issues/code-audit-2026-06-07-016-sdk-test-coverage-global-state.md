---
title: 'SDK: 测试覆盖严重不足 + 模块级可变全局状态'
status: open
severity: medium
category: architecture
location: squirrel-sdk/tests/test_http.py, src/crawl/http.py:160-161, src/crawl/utils.py:22-23, src/crawl/config.py:10
---

## 问题描述

### 测试覆盖
整个 SDK 仅 1 个测试文件（`tests/test_http.py`）含 2 个测试方法，仅覆盖 Cloudflare 异步桥接。以下模块零测试：
- 核心数据模型（VideoMeta、ExtractionResult、ExtractionTask）
- Protocol 接口
- VideoExtractorBase、BaseImporter、PaginatedImporter
- 限速器、配置管理、cookie 工具、代理 helper、playlist 重写
- SiteRuntime、异常体系、yt-dlp 工具

### 全局可变状态
多个模块依赖可变模块级全局变量：
- `http.py`: `_default_rate_limiter`、`_shared_session`、`_cloudflare_bypass_client`
- `utils.py`: `_cookie_file_resolver`、`_cookie_domain_resolver`
- `config.py`: `_site_configs`

无锁保护（`_session_lock` 除外），测试需手动保存/恢复状态。

## 影响

- 核心数据模型序列化回归无法被捕获
- 测试不能并行运行
- 多站点插件存在竞态条件

## 建议方向

1. 至少增加：VideoMeta 序列化、ExtractionResult 往返、ExtractionTask 幂等 ID、异常体系行为、配置 get/set、RateLimiter 定时逻辑的单元测试
2. 考虑 `SdkContext` 上下文对象持有所有可变状态，通过依赖注入传递给插件
3. 短期内至少记录线程安全的文档说明
