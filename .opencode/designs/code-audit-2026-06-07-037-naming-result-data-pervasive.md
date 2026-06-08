# 命名修复方案 — issue 037

## 根因

项目缺乏统一命名规范，导致 `result`/`data`/`info` 作为无语义通用变量泛滥（~200+ 处），降低可读性和 grep 效率。

## 修复思路（按子项目分批）

### Batch A: SDK（squirrel-sdk/）— 最小化
- `data` 作为 `from_dict(cls, data: dict[str, Any])` 参数是 Python 数据类反序列化的通用惯例，**不改**（10 处 in core.py, 7 处 in runtime_models.py）
- `result` 改具体名：`http.py:189` `_resolve_maybe_async_result` → 保持不动（已经是描述性函数名）；`site_runtime.py:70` `result` → `response`；`core.py:212` `result: ExtractionResult` → `extraction_result`
- **涉及文件：** `src/crawl/site_runtime.py`, `src/crawl/core.py`

### Batch B: 后端 backend（squirrel-backend/）
- **`result` 改具体名：** 按上下文映射为 `users`, `configs`, `response`, `task`, `record`, `video_info` 等
  - `scheduler.py`（11 处）→ `update_result` / `sync_result` / `scheduled_task`
  - `routes/subscription.py`（6 处）→ `schedule_result` / `run_result` / `history_result`
  - `routes/scheduler.py`（5 处）→ `task_result`
  - `site_catalog_service.py`（8 处）→ `normalized_config`
  - `default_strategy.py`（4 处）→ `execute_result` / `sync_result`
  - 其余 1-3 处各处逐一映射
- **`data` 参数改具体名：** 仅在明确场景改，`from_dict` 类方法不改
  - `common/response.py` → `data` 保持（它是通用响应包装器，参数名合理）
  - `jwt_helper.py:32` `data: dict` → `payload: dict`
  - CRUD 方法 `data: dict` → `record: dict` / `create_data`
- **`info` 改具体名：** `for slug, info in catalog.items()` → `for slug, site_info in catalog.items()`
  - 涉及 6+ 个 service 文件
- **`msg` 不改：** `common/response.py` 的 `msg` 字段是 API 响应格式的一部分，前端有依赖，改为 `message` 是 breaking change
- **`Auth`/`Authentication` 统一：** `auth.py:54` `AuthMiddleware` → `AuthenticationMiddleware`

### Batch C: 前端 frontend（squirrel-frontend/）
- **`result` 改具体名：** 每个 composable 中 `const result` → `const response` / `const data` / 具体业务名
  - 涉及 ~39 处 `const result = await ...` 模式
- **`data` 参数改具体名：** HTTP 方法参数 `data?: unknown` 保持（通用函数合理），但业务函数改
  - `useUser.ts` `data: Record<string, unknown>` → `credentials` / `profile`
- **`info` 不改：** `errorHandler.ts:58` `info: string` 是 Vue 官方约定（`vueErrorHandler` 签名）
- **`.js` → `.ts` 迁移：** 4 个 .js 文件重命名为 .ts + 加类型注解（本次不做——涉及类型推断和导入兼容，需独立 issue）

### Batch D: 桌面端 desktop（squirrel-desktop/）
- **`result` 改具体名：** test 文件 16 处 `const result` → `const videos` / `const channel` / `const response`；provider 中同理
- **`info` 改具体名：** `youtubei_core.mjs` → `videoInfo` / `streamingInfo`；`bilibili/index.mjs` → `videoInfo`

### 红线检查
- `site_runtimes/` 下的 .py 文件：不碰（包含 youtube/subscription.py 中的 `info` 问题）
- 不改 .env / 凭据
- 不改未涉及子项目：合法——本 issue 覆盖全项目命名，但 .js→.ts 迁移暂不纳入

## 涉及文件（按 Batch）

| Batch | 子项目 | 文件数 |
|-------|--------|--------|
| A | SDK | 2 |
| B | Backend | ~25 |
| C | Frontend | ~18 |
| D | Desktop | ~7 |

## 潜在风险
1. `common/response.py` 不改——API 响应 `msg` 字段名不动
2. `from_dict(cls, data: dict)` 不改——SDK 惯例不动
3. 前端 `info` 在 `errorHandler.ts` 不改——Vue 官方约定
4. `.js` → `.ts` 暂不迁移——需独立处理导入兼容
5. 测试中 `result` 改名不影响逻辑（仅变量名）
