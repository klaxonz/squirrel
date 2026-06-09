# 修复 Backend httpx AsyncClient 资源泄漏

## 根因

1. **MusicClient** (`_client.py:29`) — `__init__` 中无条件创建 `httpx.AsyncClient`，但无任何关闭路径。调用方 `MusicService` 每次请求都新建实例（FastAPI `Depends`），导致连接池泄漏。

2. **ThumbnailDownloaderService** (`thumbnail_downloader.py:75-82`) — 同步 `httpx.Client` 懒初始化，仅在 `_reset_http_client()`（transport error 回退）时关闭。模块级单例无优雅关闭出口。

3. **MetricsService** (`metrics_service.py:43,108,179,251,316`) — 使用 `next(get_db())` 绕过上下文管理器，依赖 `finally: db.close()` 触发 generator cleanup。如果异常路径不调用 `db.close()`，Session 不会归还连接池。

## 修复思路

### 1. MusicClient — 添加 `aclose()` 生命周期管理
- `MusicClient`: 添加 `async def aclose()`，只在 `self.http_client` 不是外部注入时关闭
- `MusicService`: 添加 `async def aclose()`，委托给 `self._client.aclose()`
- `routes/music.py:get_music_service`: 改为 `async def` 带 `yield` 的 FastAPI dependency，`finally` 中调用 `await service.aclose()`

### 2. ThumbnailDownloaderService — 添加 `close()` 方法
- `ThumbnailDownloaderService`: 添加 `def close()`，关闭 `self._http_client`
- `_reset_http_client`: 复用 `close()` 的实现

### 3. MetricsService — 替换为 `with get_session()`
- 所有 5 处 `db = next(get_db()); try/except/finally: db.close()` 改为 `with get_session() as db:`，简化异常处理

## 涉及文件

| 文件 | 修改 |
|------|------|
| `services/music/_client.py` | 添加 `aclose()` |
| `services/music/__init__.py` | 添加 `MusicService.aclose()` |
| `routes/music.py` | `get_music_service` 改为 yield dependency |
| `services/extraction/thumbnail_downloader.py` | 添加 `close()`，复用 |
| `services/metrics_service.py` | 5 处 `next(get_db())` → `with get_session()` |

## 潜在风险

- `MusicService` 在音乐路由之外无人使用（已验证），改变 dependency 不波及其它路由
- `ThumbnailDownloaderService.close()` 作为新方法当前无外部调用者，仅提供优雅关闭能力
- `MetricsService` 从 `get_db()` 改为 `get_session()` 行为一致（`get_db()` 本身就是 `with get_session()` 的封装）
