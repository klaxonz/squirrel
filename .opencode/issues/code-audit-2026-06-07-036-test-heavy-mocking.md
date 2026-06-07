---
title: 测试 — 后端过度 Mock（1190 处 patch/monkeypatch）
status: fixed
fixed_by: services/music/__init__.py (first DI service), services/video_history_service.py (session_factory DI), services/system_config_service.py (session_factory DI), services/*.py (60+ services converted to class-based DI)
severity: medium
category: test-quality
location: squirrel-backend/tests/（全量 89 个测试文件）
---

## 问题描述

后端测试共使用 1190 次 mock/patch/monkeypatch，平均每个测试文件 13+ 次。严重依赖内部实现细节：

**Top 10 最高 mock 文件：**
| 文件 | Mock 数 |
|------|---------|
| `tests/services/test_music_service.py` | 163 |
| `tests/test_app_runtime_bootstrap.py` | 87 |
| `tests/services/test_subscription_service.py` | 89 |
| `tests/services/test_subscription_update_strategy.py` | 65 |
| `tests/core/test_thumbnail_downloader_service.py` | 59 |
| `tests/services/test_subscription_sync_end_to_end_runs.py` | 42 |
| `tests/services/test_subscription_update_scheduler.py` | 41 |
| `tests/services/test_video_service.py` | 41 |
| `tests/processes/test_crawl_worker_runtime.py` | 39 |
| `tests/services/test_video_history_service.py` | 36 |

典型脆弱模式：
- `sys.modules` 注入假模块（`bootstrap.py`、`subscription_service.py`）
- monkeypatch 修改模块级变量/函数引用
- 定义 6+ 假 client 类 mock 内部 HTTP 调用
- 测试断言方法调用参数（而非行为结果）

## 影响

- 重构时大量测试需要同步修改（即使行为未变）
- mock 越多，测试越少价值——测的是实现而非契约
- 新人难以理解 mock 链

## 建议方向

1. 对 service 层测试，优先使用 real DB（测试容器/内存 SQLite）而非 mock session
2. 对外部 HTTP 调用，使用 `responses` / `pytest-httpx` 库 mock 网络层（而非 mock 业务方法）
3. 逐步将高 mock 文件重构为集成测试 + 少量 mock 的混合模式
4. 引入契约测试（接口不变则测试不变）
