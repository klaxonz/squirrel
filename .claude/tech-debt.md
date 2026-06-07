# 技术债务清单

> 创建时间: 2026-06-06
> 最后更新: 2026-06-07

## 状态说明
- 🔴 待处理
- 🟡 进行中
- ✅ 已完成
- ⏸️ 暂停/延后

## 工作流程

修复代码时发现的新问题，追加到清单末尾（编号递增），任务完成后统一处理。

---

## 🔴 待处理

### TD-021: 前端播放器核心过度集中
- **位置**:
  - `squirrel-frontend/src/components/video-player/VideoPlayer.vue` (约 3066 行)
  - `squirrel-frontend/src/components/video-player/core/createPlayerEngine.ts` (约 1187 行)
- **问题**: 播放器核心同时处理 DOM 绑定、媒体状态、插件调度、错误恢复、清晰度、字幕、进度、全屏、画中画和音量增益；plugin/core/runtime 分层存在，但实际仍是巨型状态机。
- **影响**: 播放问题排查成本高，新增能力容易继续堆进大文件，`pluginManager.get<any>()` 让类型边界失效。
- **方案**: 按媒体元素生命周期、错误恢复、字幕、进度、质量控制拆分模块；插件接口改为显式能力类型，恢复策略收敛到单一入口。

### TD-028: 前端 API 层默认 `any` 弱化数据契约
- **位置**: `squirrel-frontend/src/utils/request.ts`
- **问题**: `RequestResult<T = any>`、`get<T = any>`、`post<T = any>` 和 `catch (err: any)` 让调用方很容易不声明返回类型。
- **影响**: 后端 DTO 变化不容易被前端类型检查发现，组件继续出现 `(result.data as any)`。
- **方案**: 默认泛型改为 `unknown`；为高频 API 建立具体 response type；业务错误 code 使用窄类型。

---

## ⏸️ 延后项

### TD-003: 重复的数据库会话模式
- **位置**: 所有服务文件 (200+ 处)
- **问题**: `with get_session() as session:` 模式大量重复
- **方案**: 引入 Repository 模式或 Unit of Work 模式
- **影响**: DRY 原则，测试困难
- **延后原因**: 当前 get_session() 上下文管理器已足够简洁，投入产出比不高

### TD-006: 前端组件过大
- **位置**: `squirrel-frontend/src/views/VideoPlay.vue` (718行)
- **问题**: 组件承担过多职责
- **方案**: 拆分为播放器、控制栏、信息面板等子组件
- **影响**: 可维护性
- **延后原因**: 组件已通过 composables 实现逻辑分离，模板部分虽长但结构清晰，投入产出比不高

### TD-005: RESTful 语义不统一（剩余部分）
- **问题**: 部分 API 使用 RPC style（如 `/api/subscription/subscribe`、`/api/video-interaction/toggle-like`）
- **方案**: 改为 REST style（如 `POST /api/subscriptions`、`PUT /api/video-interactions/{id}`）
- **影响**: API 设计一致性
- **延后原因**: 涉及破坏性 API 变更，需前后端同步改造

---

## ✅ 已完成

### TD-022: 播放会话 store 使用 `any` 承载核心跨页面契约
- **位置**: `squirrel-frontend/src/stores/player.ts`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 新增 `types/playerSession.ts`，定义 `PlayerSessionState`、`PlaylistEntry`、`PlayerHandlers`、`ExternalErrorState` 显式接口
  - `stores/player.ts` 所有 `any` 字段替换为显式类型；`activateSession(payload: Partial<PlayerSessionState>)` 替代 `payload: any`
  - `usePlaybackOrchestrator.ts` 的 `ExternalErrorState` 定义迁移到 `types/playerSession.ts` 并 re-export
  - `useVideoPlaybackShell.ts` 移除局部 `ActivateSessionPayload` / `GlobalPlaybackSessionLike` 类型，改用 `PlayerSessionState` 族
  - `GlobalVideoPlayerHost.vue` 移除 4 处 `as any` 转型，显式标志 clipMarkers 类型边界

### TD-029: 桌面主进程仍过大
- **位置**: `squirrel-desktop/src/main.mjs` (原约 1931 行，现 84 行)
- **完成时间**: 2026-06-07
- **修复内容**:
  - main.mjs 精简为纯组合根（app lifecycle + renderer URL resolve + 启动编排），仅 84 行
  - 新增 `constants.mjs`：集中管理 Chrome UA、站点 origin/pattern 常量、文件路径等
  - 新增 `cookie-header.mjs`：Cookie 目标检测（isJavdbCookieTarget 等）、Netscape cookie 文件读取、mergeCookieHeaders
  - 新增 `site-login.mjs`：站点登录 profiles/aliases、登录态检测（javdb/pornhub/youporn/youtube）、登录窗口管理、会话清除、buildCookieHeaderForUrl
  - 新增 `document-loader.mjs`：Camoufox 文档加载、BrowserWindow HTML 抓取、createSessionFetch
  - 新增 `media-headers.mjs`：MEDIA_HEADER_RULES 媒体请求头注入、跨域响应头松弛
  - 新增 `shell-pages.mjs`：Shell 错误页面 HTML 构建 (buildShellPageUrl/showErrorShell)
  - 新增 `ipc-handlers.mjs`：所有 IPC handler 按功能注册（播放/search/站点登录/窗口/服务端配置）
  - 新增 `window.mjs`：窗口创建、导航、键盘/菜单/上下文菜单行为
  - 播放 provider 保持独立，不受影响
  - 更新 site-login.test.mjs 和 youtube-provider.test.mjs 指向新模块路径

### TD-030: 仓库内参考代码和 IDE shelf 污染代码扫描
- **位置**:
  - `output/_refs/`
  - `.idea/shelf/`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 两个目录均属非项目产物（BewlyCat 参考代码、IDEA shelved patches），已删除
  - gitignore 规则已覆盖，无需额外配置

### TD-031: 后端 logger 使用不一致
- **位置**: `squirrel-backend/routes/video.py`、`squirrel-backend/routes/base.py`、`squirrel-backend/queues/consumer.py`、`squirrel-backend/utils/rate_limiter.py` 等
- **完成时间**: 2026-06-07
- **修复内容**:
  - 37 处 `logging.getLogger()` 根 logger 全部替换为 `logging.getLogger(__name__)`
  - 涉及 36 个文件（routes、services、queues、utils、schedule、processes、core 等）
  - `system_config_service.py` 新增模块级 logger，替换 3 处 `logging.getLogger().info/debug()` 直调

### TD-032: broad exception 分布过广
- **位置**: 后端、SDK、site runtime 多个中间层模块
- **完成时间**: 2026-06-07
- **修复内容**:
  - 后端 utils: cookie.py(6), site_catalog.py(3), url_helper.py(1), cloudflare_bypass.py(1) 窄化异常类型
  - 后端 site_runtimes: supervisor.py(3), store.py(1), runtime_bridge.py(4), reload_listener.py(3) 窄化/注释
  - 后端 core: site_config_manager.py(3), cookie_config.py(2), dynamic_task_manager.py(7), extraction 各模块(10+), streaming/proxy.py(5) 窄化
  - 后端 services: metrics_service.py(6), rss/service/account/sync(6+), subscription 各模块(8+), 其他 service(8+) 窄化
  - 后端 queues: message.py(1), producer.py(2), duplicate_checker.py(3), queue_monitor.py(1) 窄化
  - 后端 common: log.py(2) 窄化
  - 后端 routes: 26 处 HTTP API 边界添加注释说明边界性质
  - 后端 main/processes/schedule/consumer: 32 处启动/进程/任务/消费者边界添加注释
  - SDK: utils.py(6), proxy_helpers.py(1), importer.py(1), extractor.py(1 改进+注释), site_runtime.py(1 注释)
  - Site runtimes: bilibili/youtube/pornhub/youporn/javdb 共 24 个文件中的 except 窄化或加边界注释

### TD-026: Redis Stream consumer 重试和死信模型不完整
- **位置**:
  - `squirrel-backend/queues/consumer.py`
  - `squirrel-backend/queues/__init__.py`
  - `squirrel-backend/tests/queues/test_consumer.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 新增显式 `QueueHandler` protocol，consumer handler 固定接收消息 body，不再用签名长度猜测是否传入 stream
  - `ConsumerOptions` 新增显式失败策略：`retry`、`dlq`、`ack_delete`
  - `dlq` 策略强制配置 `retry_dlq`，避免失败消息因配置缺失长期隐式滞留
  - `start_loop()` 支持 `stop_event`，便于进程停止和单元测试控制
  - 新增 Redis Stream consumer 单元测试覆盖失败策略、DLQ、handler 调用约定和停止信号

### TD-027: 站点 runtime supervisor 职责过重
- **位置**:
  - `squirrel-backend/site_runtimes/supervisor.py`
  - `squirrel-backend/site_runtimes/process_launcher.py`
  - `squirrel-backend/site_runtimes/transport.py`
  - `squirrel-backend/site_runtimes/audit.py`
  - `squirrel-backend/site_runtimes/health.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 拆出 process launcher，负责端口选择、命令构造、环境变量、runtime cwd、日志流和 `Popen` 启动
  - 拆出 transport client，集中处理 runtime HTTP JSON 请求
  - 拆出 audit writer，集中处理 runtime 日志/审计产物路径与审计 JSONL 写入
  - 拆出 health checker，集中处理 `/health` 拉取、启动等待和 health snapshot 转换
  - supervisor 保留 runtime 状态编排、expiry timer、停止进程、invoke 审计和错误映射

### TD-025: 后端路由层承担过多业务编排和异常翻译
- **位置**:
  - `squirrel-backend/routes/video.py`
  - `squirrel-backend/services/video_subtitle_service.py`
  - `squirrel-backend/site_runtimes/gateway.py`
  - `squirrel-sdk/src/crawl/runtime_errors.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 新增字幕 service，路由不再负责视频查询、domain 解析、runtime 调用和 runtime 错误映射
  - runtime route miss 改为稳定 `PLUGIN_ROUTE_NOT_FOUND` code
  - 字幕不可用改为稳定 `SUBTITLES_NOT_AVAILABLE` code，不再依赖 error message substring
  - `/api/video/subtitles` 路由只保留 HTTP response 组装和 service error 到 HTTP status 的最终映射

### TD-024: 后端启动流程混入隐式降级初始化
- **位置**:
  - `squirrel-backend/main.py`
  - `squirrel-backend/routes/base.py`
  - `squirrel-backend/routes/health.py`
- **方案**: 将 site config override、cookie resolver、runtime bootstrap、projection seed 定为 required；Cloudflare bypass 与 scheduled task bootstrap 定为 optional，并把 optional 降级暴露到 `/health`。
- **完成时间**: 2026-06-07

### TD-023: Runtime V2 目标明确但后端仍大量依赖全局 manager
- **位置**:
  - `squirrel-backend/site_runtimes/ports.py`
  - `squirrel-backend/core/streaming/proxy.py`
  - `squirrel-backend/core/extraction/factory.py`
  - `squirrel-backend/routes/video.py`
  - `squirrel-backend/utils/url_helper.py`
  - `squirrel-backend/utils/site_catalog.py`
  - `squirrel-backend/services/subscription_import_service.py`
  - `squirrel-backend/services/site_login_status_service.py`
  - `squirrel-backend/services/subscription_update/strategies/default_strategy.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 新增 `site_runtimes/ports.py`，将全局 manager 访问收敛到 runtime gateway/snapshot 端口
  - `VideoProxy`、`ExtractorFactory`、订阅导入、登录检测和订阅更新策略改为接收 `SiteRuntimeGateway`
  - `url_helper`、`SiteCatalog` 改为接收 runtime snapshot，测试不再 monkeypatch manager 单例
  - 保留 `site_runtime_service` 和 manager 生命周期函数作为 runtime 管理组合根

### TD-015: 后端提取任务兼容入口残留
- **位置**:
  - `squirrel-backend/core/extraction/task_manager.py`
  - `squirrel-backend/core/extraction/handlers/video_handler.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 删除 `TaskManager.__init__` 的 `queue_mapping` 参数
  - 删除未被生产路径调用的 `TaskRouter`、`submit_task` 和 `process_task`
  - 删除 `VideoExtractionHandler.handle_success` 的兼容实现，保留当前 Pipeline 入口

### TD-020: 本地运行期产物体积大
- **位置**:
  - `squirrel-backend/radar.db`
  - `squirrel-site-runtimes/*/runtime-logs/`
  - `squirrel-site-runtimes/*/runtime-audit/`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 新增 `scripts/clean-local-runtime-artifacts.ps1`
  - 支持 `-DryRun` 预览清理目标
  - 仅清理本地 SQLite 状态和 runtime logs/audit，不触碰配置、cookie 或下载数据

### TD-019: 桌面主进程职责过重（第一阶段）
- **位置**:
  - `squirrel-desktop/src/main.mjs`
  - `squirrel-desktop/src/window-state.mjs`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 将窗口状态默认值、读取、保存、事件绑定迁移到 `window-state.mjs`
  - `main.mjs` 只负责传入 Electron `userData` 路径并使用结果创建窗口
  - 新增 `tests/window-state.test.mjs` 覆盖默认状态、尺寸清洗、保存与最小化跳过
- **后续拆分建议**: `site-login`、`cookie-header`、`media-headers`、`ipc-handlers`

### TD-018: 视频播放器重构后的测试债
- **位置**: `squirrel-frontend/src/components/video-player/REFACTOR_PLAN.md`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 按仓库“前端不再维护、不新增、不运行测试”约定，不引入前端测试框架或测试用例
  - 将 Phase 5 收敛为专项手工回归清单
  - 覆盖基础加载、播放源切换、质量降级、字幕渲染、快捷键、销毁清理

### TD-017: 订阅视频持久化缺少全量/增量语义
- **位置**: `squirrel-backend/core/extraction/services/video_persistence.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - `extract_video` 生成任务时写入明确 `sync_mode`
  - `PersistenceStage` 将同步模式传给 `VideoPersistenceService`
  - `subscription_video_service.create_subscription_video` 增加显式 `refresh_feed` 参数
  - 增量同步创建新关联时刷新用户 feed，全量同步只建立订阅-视频关联
  - 新增服务测试覆盖 full / incremental 差异

### TD-016: `SchedulerStatus.legacy_tasks` 旧字段残留
- **位置**: `squirrel-backend/models/scheduler_status.py`
- **完成时间**: 2026-06-07
- **修复内容**:
  - 删除 `SchedulerStatus.legacy_tasks` 模型字段
  - 新增 Alembic migration 删除 `scheduler_status.legacy_tasks`

### TD-001: 临时目录残留
- **位置**: `squirrel-backend/scratch/`
- **方案**: 删除目录并添加到 .gitignore
- **完成时间**: 2026-06-06

### TD-002: 服务文件过大
- **位置**:
  - `squirrel-backend/services/video_service.py` (985行)
  - `squirrel-backend/services/subscription_service.py` (1135行)
  - `squirrel-backend/services/rss_service.py` (1700+行)
- **问题**: 违反单一职责原则，难以维护
- **方案**: 按职责拆分为多个模块
- **完成时间**: 2026-06-06
- **拆分结果**:
  - video_service.py → video_crud_service.py, video_list_service.py, video_list_query_service.py, video_random_service.py
  - subscription_service.py → subscription_crud_service.py, subscription_list_service.py, subscription_manage_service.py, subscription_import_service.py
  - rss_service.py → rss_credential_service.py, rss_client_service.py, rss_account_service.py, rss_sync_service.py
- **修复记录**: 2026-06-06 修复类型导入缺失和模块导入错误

### TD-004: NSFW 站点硬编码
- **位置**: `squirrel-backend/services/subscription_service.py:359-362`
- **方案**: 改为配置驱动，通过 `SiteCatalog.find_site_by_domain` 获取站点配置中的 `metadata.nsfw` 字段
- **完成时间**: 2026-06-06

### TD-005: API 路由注册方式不统一
- **问题**:
  - 部分路由用 `APIRouter(prefix=...)` 注册，部分用内联完整路径，代码风格不一致
  - `/api/video/remote/save` 用路径层级而非连字符，与其余路由风格不符
- **完成时间**: 2026-06-06
- **修复内容**:
  - 所有 10 个内联路径路由文件统一改用 `APIRouter(prefix=...)` 注册方式
  - `/api/video/remote/save` → `/api/video/remote-save`（连字符风格统一）
  - 前端 `api/video.ts` 同步更新
- **备注**: URL 路径段本身一直使用连字符风格，无下划线或驼峰

### TD-007: 类型定义过度可选
- **位置**: `squirrel-frontend/src/types/videoPlayback.ts:32-51`
- **方案**: 区分必填字段和可选字段，移除冗余的 `| null`
- **完成时间**: 2026-06-06
- **修改范围**: videoPlayback.ts, playlist.ts, videoClipMarker.ts, useVideoActionBar.ts, VideoPlay.vue

### TD-008: 静默异常吞没
- **位置**: 后端路由和服务文件
- **方案**: 修复关键的静默异常吞没，添加日志记录
- **完成时间**: 2026-06-06
- **修复内容**:
  - routes/rss.py: 后台 RSS 同步异常添加 logger.exception
  - routes/sites.py: OAuth 状态获取失败添加 logger.warning
  - 其他 `except: pass` 多为清理/工具函数中的最佳努力语义，保持现状

### TD-008: 错误响应格式统一（剩余部分）
- **位置**: `routes/base.py` 全局异常处理器、`routes/scheduler.py`
- **方案**: 全局异常处理器改用 ErrorCode 常量，统一错误响应格式
- **完成时间**: 2026-06-06
- **修复内容**:
  - routes/base.py: 全局异常处理器 code 字段从 -1 改为对应 ErrorCode 常量（400/401/404/500）
  - routes/scheduler.py: 从 raise HTTPException + raw dict 全面迁移到 common.response helpers
  - 现在所有 API 错误响应统一为 `{"code": <ErrorCode>, "msg": "...", "data": null}` 格式
  - health/connectivity 端点为诊断接口，保留自有格式

### TD-009: 路由层与服务层魔法字符串
- **位置**: 路由层（`squirrel-backend/routes/video.py`）与后端/SDK/插件各模块状态定义
- **方案**: 将硬编码字符串和 `(str, Enum)` 全面替换/升级为 `StrEnum`（SDK和插件使用兼容性回退机制）
- **完成时间**: 2026-06-06
- **修改内容**:
  - 路由层全面使用 `StrEnum`（如 `VideoCategory`, `YesNoAll` 等）
  - 迁移后端全部 `(str, Enum)` 状态枚举为内置 `StrEnum`（包括 `SyncStatus`, `CrawlTaskStatus`, `TaskType` 等）
  - 迁移 SDK 及 bilibili 插件内部 `(str, Enum)` 为 `StrEnum`（使用兼容性 fallback 块确保 Python 3.10 兼容性）

### TD-010: 分页参数命名不一致
- **位置**: `squirrel-backend/routes/video.py:57-58`, `routes/subscription.py:99`
- **方案**: 保持现状，使用 `alias="pageSize"` 桥接前端驼峰和 Python 下划线是合理设计
- **完成时间**: 2026-06-06

### TD-011: 目录命名不规范
- **位置**: `squirrel-backend/sqlfile/` → `squirrel-backend/sql/`
- **方案**: 重命名为 `sql/`，更新导入路径
- **完成时间**: 2026-06-06

### TD-012: Python 类型注解不完整
- **位置**: 服务层大部分函数
- **方案**: 逐步补充类型注解
- **完成时间**: 2026-06-06
- **修复内容**:
  - Tier 1: video_query.py (14), video_list_query_service.py (9), subscription_sync_center_service.py (13), search_suggestion_service.py (11)
  - Tier 2: subscription_list_service.py (7), subscription_sync_projection_service.py (7), subscription_sync_state_service.py (8), subscription_sync_history_service.py (6), crawl_dispatcher/service.py (6), video_extraction_center_service.py (5)
  - Tier 3: rss_client_service.py, subscription_sync_event_service.py, subscription_video_service.py, video_list_service.py, video_history_service.py, user_service.py, user_video_feed_service.py, rss_account_service.py, video_clip_marker_service.py, playlist_service.py, crawl_tasks/service.py, rss_sync_service.py, subscription_update/strategies/registry.py, outbox_event_service.py, creator_service.py, video_creator_service.py, video_interaction_service.py, subscription_update/strategies/base.py
  - 主要模式: 添加 `Session` 类型注解到所有 session 参数，为 SQL 查询工具函数添加 `Any` 返回类型，补充 `__init__` 方法的 `-> None` 注解

### TD-013: 前端 API 层类型过于宽松
- **位置**: `squirrel-frontend/src/api/video.ts`
- **方案**: 定义 VideoListParams 和 RandomVideoParams 替代 Record<string, unknown>
- **完成时间**: 2026-06-06

### TD-014: Composable 职责过重
- **位置**: `squirrel-frontend/src/composables/useVideoHistory.ts` (361行)
- **方案**: 拆分为 useVideoHistorySync.ts (本地状态/同步引擎) + useVideoHistory.ts (API 操作)
- **完成时间**: 2026-06-06

---

## 统计

| 状态 | 数量 |
|------|------|
| ✅ 已完成 | 29 (TD-001, 002, 004, 005, 007, 008, 008-rest, 009, 010, 011, 012, 013, 014, 015, 016, 017, 018, 019-stage1, 020, 022, 023, 024, 025, 026, 027, 029, 030, 031, 032) |
| ⏸️ 延后 | 3 (TD-003, 005-rest, 006) |
| 🔴 待处理 | 2 (TD-021, 028) |

---

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-06-06 | 创建技术债务清单 |
| 2026-06-06 | 完成 TD-001: 删除 scratch 目录 |
| 2026-06-06 | 完成 TD-004: NSFW 改为配置驱动 |
| 2026-06-06 | 完成 TD-010: 确认分页参数设计合理 |
| 2026-06-06 | 完成 TD-002: 拆分服务文件 (video, subscription, rss) |
| 2026-06-06 | 延后 TD-003: 重复的数据库会话模式 |
| 2026-06-06 | 完成 TD-005: 统一路由注册方式 + 修复 remote/save 命名 |
| 2026-06-06 | 延后 TD-006: 前端组件过大 |
| 2026-06-06 | 完成 TD-007: 类型定义去除冗余 `| null` |
| 2026-06-06 | 完成 TD-008: 修复关键路径静默异常吞没 |
| 2026-06-06 | 完成 TD-009: 路由层魔法字符串替换为枚举 |
| 2026-06-06 | 完成 TD-011: 重命名 sqlfile/ 为 sql/ |
| 2026-06-06 | 完成 TD-013: 前端 API 层添加具体类型 |
| 2026-06-06 | 完成 TD-014: 拆分 useVideoHistory composable |
| 2026-06-06 | 完成 TD-012: 补充服务层类型注解 (80+ functions across 30+ files) |
| 2026-06-06 | 整理文档结构: 去重已完成条目，拆分部分完成项为「已完成 + 延后剩余」 |
| 2026-06-06 | 完成 TD-008 剩余: 全局异常处理器 code 统一为 ErrorCode，scheduler 迁移到 common.response |
| 2026-06-06 | 完成 TD-009 剩余: 迁移所有 (str, Enum) 为 StrEnum（SDK/插件通过 try-except 兼容 3.10），彻底消除服务层及 SDK 的魔法字符串与旧 Enum 混用问题 |
| 2026-06-07 | 新增 TD-015~TD-020: 记录提取任务兼容入口、legacy_tasks、订阅持久化语义、播放器测试、桌面主进程职责和本地运行产物问题 |
| 2026-06-07 | 完成 TD-015: 删除后端提取任务兼容入口残留 |
| 2026-06-07 | 完成 TD-020: 新增本地运行期产物清理脚本 |
| 2026-06-07 | 完成 TD-016: 删除 SchedulerStatus legacy_tasks 字段并新增删除列 migration |
| 2026-06-07 | 完成 TD-017: 订阅视频持久化显式区分 full/incremental feed 刷新语义 |
| 2026-06-07 | 完成 TD-018: 播放器 Phase 5 收敛为专项手工回归清单 |
| 2026-06-07 | 完成 TD-023: Runtime gateway/snapshot 端口注入业务层，manager 单例收敛到组合根 |
| 2026-06-07 | 完成 TD-019 第一阶段: 拆分桌面窗口状态模块并补 Node 测试 |
| 2026-06-07 | 新增 TD-021~TD-032: 记录全面代码分析发现的播放器、runtime、启动、队列、API 类型、桌面主进程、扫描噪音和异常处理技术债 |
| 2026-06-07 | 完成 TD-024: 后端启动依赖显式区分 required/optional，optional 降级暴露到 health |
| 2026-06-07 | 完成 TD-022: 播放会话 store `any` 字段全部替换为显式类型，新增 `types/playerSession.ts` |
| 2026-06-07 | 完成 TD-025: 字幕获取编排移入 service，runtime route miss 和字幕不可用改用稳定错误 code |
| 2026-06-07 | 完成 TD-027: 拆分 runtime supervisor 的 process launcher、transport client、audit writer 和 health checker |
| 2026-06-07 | 完成 TD-026: Redis Stream consumer 改为显式 handler protocol、失败策略和 stop event |
| 2026-06-07 | 完成 TD-032: 全面窄化中间层 except Exception 为具体异常类型或添加边界注释（后端 utils/site_runtimes/core/services/queues/routes/main/processes/schedule/consumer + SDK + site runtimes 共 80+ 文件） |
| 2026-06-07 | 完成 TD-029: 桌面主进程从 2174 行精简为 84 行组合根；拆分为 constants/cookie-header/site-login/document-loader/media-headers/shell-pages/ipc-handlers/window 8 个模块；更新 site-login/youtube-provider 测试 |
