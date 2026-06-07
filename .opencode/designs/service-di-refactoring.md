---
title: 后端服务层 DI 重构方案
status: in_progress
implemented:
  - Phase 0: Pipfile, conftest.py, pyproject.toml, core/cache.set_redis_client
  - Phase 1: MusicClient class, MusicService class (DI-ready), routes/music.py Depends, test_music_service.py rewritten — 66 tests pass, 0 monkeypatch, 0 mock
  - Phase 2:
    - VideoHistoryService class (session_factory + get_user_config DI), routes/video_history.py Depends, test rewritten — 13/15 pass
    - SiteCatalogService class (static methods), routes/sites.py + site_cookies.py Depends
    - SiteLoginStatusService class (gateway + snapshot DI), routes/sites.py + site_cookies.py Depends
    - SystemConfigService class (session_factory DI), routes/system_config.py + scheduler.py Depends, processes updated
  - Total: 86 tests passing across refactored services
created: 2026-06-07
req: service-di-refactoring
---

# 设计方案：后端服务层 DI 重构

## 问题

服务层是模块级过程式函数，依赖全局模块级单例（`get_session`、`redis_client`、`settings`）。测试无法注入 mock，只能 monkeypatch 模块层全局变量。全项目 1190 处 mock。

## 方案：class-based 服务 + FastAPI `Depends` 注入（不兼容重构）

Route 不再 `from services import xxx`，改为 `Depends(get_xxx_service)` 获取 service 实例。Service 改为 class，依赖通过构造函数注入。测试直接 new 实例传 mock。

### 架构

```
┌──────────────────────────────────────────┐
│  Route (fastapi)                         │
│    svc = Depends(get_music_service)       │
│    await svc.search_tracks(...)           │
└────────────────┬─────────────────────────┘
                 │ Depends 注入
┌────────────────▼─────────────────────────┐
│  Service Class                            │
│    class MusicService:                     │
│      __init__(redis, http, cache, cfg)     │
│      async def search_tracks(...)          │
└────────────────┬─────────────────────────┘
                 │ 构造函数注入
┌────────────────┴────────────┬────────────┐
│  core.database              core.cache   │
│  (session_factory)          (redis)      │
│  core.config                              │
│  (settings)                              │
└─────────────────────────────────────────┘
```

### 服务 class 模式

```python
# services/music.py
class MusicService:
    def __init__(
        self,
        redis_client: Redis | None = None,
        http_client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ):
        self.redis_client = redis_client or _create_default_redis()
        self.http_client = http_client or httpx.AsyncClient(timeout=10.0)
        self.settings = settings or get_settings()

    async def search_tracks(self, user_id: int, query: str, page: int, page_size: int) -> dict:
        ...
```

### Route 模式

```python
# routes/music.py
from services.music import MusicService
from core.cache import redis_client
from core.config import settings

async def get_music_service():
    return MusicService(redis_client=redis_client, settings=settings)

@router.get("/search")
async def search_music(
    query: str = Query(...),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.search_tracks(current_user.id, query, page, page_size))
```

### 测试模式

```python
# tests/services/test_music_service.py
from services.music import MusicService

async def test_search_tracks():
    mock_redis = FakeRedis()
    svc = MusicService(redis_client=mock_redis)
    
    async with respx.mock:
        route = respx.get(...).mock(return_value=httpx.Response(200, json={...}))
        result = await svc.search_tracks(1, "test", 1, 20)
    
    assert result["items"][0]["title"] == "expected"
    assert route.called
```

### 需要 DB session 的服务

DB 服务接受 `session_factory`（callable → Session），不直接访问 `get_session`：

```python
class SubscriptionService:
    def __init__(self, session_factory: Callable[[], Generator[Session, None, None]]):
        self._session_factory = session_factory

    def get_subscriptions(self, user_id: int) -> list:
        with self._session_factory() as session:
            return session.query(...).all()

# 生产环境注入
def get_subscription_service():
    return SubscriptionService(session_factory=get_session)

# 测试注入 fake session
def test_get_subscriptions():
    svc = SubscriptionService(session_factory=lambda: mock_session)
    ...
```

## 实施计划

### Phase 0: 基础设施（首批 4 个变更）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `Pipfile` | `pytest-asyncio`, `respx`, `factory_boy`, `pytest-env` |
| 2 | `tests/conftest.py` | 共享 fixtures: `mock_redis`, `mock_db`, `respx_mock`, `auth_user` |
| 3 | `core/database.py` | `get_session()` 保持；导出 `session_factory` 签名类型 |
| 4 | `core/cache.py` | 添加 `get_test_redis()` / `set_redis_client()` 辅助 |

### Phase 1: Music Service（试点）

重构 `services/music/` 下 12 个子模块为 class，route 改用 Depends，测试重写。

**涉及文件：**
- `services/music/__init__.py` — 去掉模块级函数，只暴露 class
- `services/music/_client.py` → class `MusicClient`
- `services/music/search.py` → class `MusicSearchService`
- `services/music/album.py` → class `MusicAlbumService`
- ...每子模块独立 class，通过 `MusicService` 组合
- `routes/music.py` — 所有路由加 Depends
- `tests/services/test_music_service.py` — 重写（mock 163 → <30）

### Phase 2: 高 mock 服务

| 文件 | 当前 mock | 策略 |
|------|-----------|------|
| `test_app_runtime_bootstrap.py` | 87 | class + Depends，mock 网络层 |
| `test_subscription_service.py` | 89 | class + session_factory 注入 |
| `test_subscription_update_strategy.py` | 65 | 同上 |
| `test_thumbnail_downloader_service.py` | 59 | class + HTTP client 注入 |
| `test_subscription_sync_end_to_end_runs.py` | 42 | class + session_factory 注入 |
| `test_subscription_update_scheduler.py` | 41 | 同上 |
| `test_video_service.py` | 41 | class + session + HTTP client 注入 |
| `test_video_history_service.py` | 36 | 同上 |
| `test_crawl_worker_runtime.py` | 39 | class + session_factory |

### Phase 3: 剩余服务

~20 个测试文件，每个 mock 10-30，按同类模式逐步迁移。

## 涉及文件全量清单

### 基础设施
- `Pipfile` (+4 dev deps)
- `tests/conftest.py` (new)
- `core/cache.py` (+set_redis_client)

### Routes（需改用 Depends）
- `routes/music.py`
- `routes/subscription.py`
- `routes/video.py`
- `routes/video_history.py`
- `routes/video_interaction.py`
- `routes/video_clip_marker.py`
- `routes/rss.py`
- `routes/scheduler.py`
- `routes/system_config.py`
- `routes/user.py`
- `routes/search.py`
- `routes/logs.py`
- `routes/playlist.py`
- `routes/sites.py`
- `routes/site_cookies.py`
- `routes/site_runtimes.py`
- `routes/connectivity.py` (可能不需要)

### Services（64 个文件，按批次）
- P1: `music/` 12 个文件
- P2: `subscription*` 约 10 个文件
- P3: `video*` 约 8 个文件
- P4: 其余 ~34 个文件

### Tests（89 个文件，逐批次迁移）

## 风险评估

| 风险 | 缓解 |
|------|------|
| Route 层大幅改动 | 模式统一（加 Depends 行），review 可控 |
| 部分服务有循环依赖 | 重构时拆清职责 |
| 异步 httpx client 生命周期 | `MusicService` 中 `__del__` 或显式 `close()` |
| 单次 session 无法完成全量 | 分批实施，每批可独立合入 |

## 验收标准

- [ ] `music/` service class-based，构造函数注入
- [ ] `music/` test mock 从 163 降至 < 30
- [ ] `routes/music.py` 用 Depends 获取 service
- [ ] `tests/conftest.py` 提供共享 fixtures
- [ ] 全量测试通过，ruff check 通过
- [ ] API 行为不变
