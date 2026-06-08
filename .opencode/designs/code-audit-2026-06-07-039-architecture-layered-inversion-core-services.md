# 修复方案：后端分层倒置

## 根因

`core/extraction/services/` 和 `utils/jwt_helper.py` 从 `services/` 导入，造成下层依赖上层的分层倒置。

## 方案

### 1. core/extraction/services/ → services/extraction/（严重）

**做法**：将 `core/extraction/services/` 物理移动到 `services/extraction/`，更新所有导入路径。

涉及文件：
- `core/extraction/pipeline/factory.py` — 从 `services/extraction/` 导入
- `services/video_history_service.py` — 同上
- `services/video_list_service.py` — 同上
- `schedule/tasks/thumbnail_refresh_task.py` — 同上
- `scripts/backfill_thumbnail_local_index.py` — 同上
- `tests/core/test_video_persistence_service.py` — 更新导入和 monkeypatch 路径
- `tests/core/test_thumbnail_downloader_service.py` — 更新导入

**风险**：低，纯路径变更，不涉及逻辑。

### 2. utils/jwt_helper → services/auth_service（中度）

**做法**：拆分 JWT 工具函数和用户查询逻辑。
- `utils/jwt_helper.py` 保留纯 JWT 函数（create/decode token、cookie 管理）
- 新建 `services/auth_service.py`，包含 `validate_auth_token()` 和 `get_current_user()`，依赖 `utils/jwt_helper` 和 `services.user_service`/`user_config_service`
- 所有路由文件从 `services/auth_service` 导入 `get_current_user`/`validate_auth_token`

涉及文件：约 20 个，全部为导入路径变更。

**风险**：中等，波及文件多但机械。

### 3. routes/sites.py → routes/connectivity（中度）

**做法**：将 `test_site_connectivity` 及其辅助函数提取到 `services/connectivity_service.py`。
- `routes/sites.py` 和 `routes/connectivity.py` 都从 services 层导入

涉及文件：
- 新建 `services/connectivity_service.py`
- 修改 `routes/connectivity.py` → 删除函数定义，改为从 services 导入
- 修改 `routes/sites.py` → 从 services 导入

**风险**：低，函数级移动。

### 4. queues/queue_monitor → services.crawl_tasks（轻度）

**做法**：`QueueBackpressureMonitor` 构造函数接受可选 `crawl_task_service` 参数，默认 `None` 时惰性导入。

涉及文件：
- 修改 `queues/queue_monitor.py`

**风险**：低。

## 向后兼容

所有变更均为纯导入路径变更，不影响对外 API 签名和响应结构。存量测试只需更新 import。
