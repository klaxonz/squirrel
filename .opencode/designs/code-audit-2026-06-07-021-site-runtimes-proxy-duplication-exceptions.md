# Issue #021 修复方案

## 根因

1. **handle_stream 死代码**：Desktop 端有独立播放流程，site-runtimes 的 proxy handle_stream 全项目零调用，Proxy 类全链路（含 BaseSiteProxy、VideoProxy protocol）无人引用
2. **Exception 滥用**：subscription.py 中 3 处直接用 `raise Exception`，上层无法针对性 catch
3. **RateLimitError 缺失**：领域异常定义了但从未实际 raise
4. **硬编码 URL/UA**：散落各处，难以维护
5. **auth.py 重复**：5 站独立实现相同 5 步流程

## 修复思路

### 1. 移除死代码
- 删除 4 站 proxy 文件中 `handle_stream` 方法、Proxy 类及相关 import（httpx、HTTPException、StreamingResponse）
- 删除 SDK 中 `VideoProxy` protocol、`BaseSiteProxy` 类
- 保留模块级 `build_runtime_proxy_config` / `rewrite_proxy_playlist`（runtime 模块在用）
- 保留 SDK 中 `ProxyDomainConfig`、`ProxyConfigProvider`（可能被 runtime 使用）
- 更新 test_javdb_proxy_runtime.py：移除依赖 JavdbProxy 类的测试，保留测试 build_runtime_proxy_config 的用例

### 2. 修复 Exception → ParseError
- javdb/subscription.py:35 改为 `raise ParseError(...)`
- pornhub/subscription.py:58,73 改为 `raise ParseError(...)`

### 3-5. 其余条目（RateLimitError、硬编码 URL/UA、auth 重复）
范围较大，需单独评估。建议确认后再推进。

## 涉及文件
- `squirrel-site-runtimes/pornhub/src/squirrel_pornhub/proxy.py`
- `squirrel-site-runtimes/javdb/src/squirrel_javdb/proxy.py`
- `squirrel-site-runtimes/youporn/src/squirrel_youporn/proxy.py`
- `squirrel-site-runtimes/youtube/src/squirrel_youtube/proxy.py`
- `squirrel-sdk/src/crawl/proxy.py`
- `squirrel-sdk/src/crawl/__init__.py`
- `squirrel-backend/tests/site_runtimes/test_javdb_proxy_runtime.py`
- `squirrel-site-runtimes/pornhub/src/squirrel_pornhub/subscription.py`
- `squirrel-site-runtimes/javdb/src/squirrel_javdb/subscription.py`

## 潜在风险
- 移除 proxy 类后如有外部依赖漏检，会导致 import error
- `safe_cookie_header_value`/`httpx` 虽当前只在 handle_stream 中用，但移除 import 后他人可能找不到
- test 文件移除后，playlist rewrite 逻辑不再有单元测试覆盖（虽有集成测试）
