# Plugin System V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current in-process plugin loader with an untrusted-plugin-safe V2 architecture based on isolated plugin runtimes, explicit RPC capabilities, and manifest-driven routing.

**Architecture:** Move plugin discovery, installation, runtime supervision, and capability routing into backend-owned services. Convert `squirrel-sdk` into a plugin-facing runtime SDK, run each plugin in a separate process, and migrate backend consumers from SDK registries to a centralized `PluginGateway`.

**Tech Stack:** FastAPI, Python subprocess/runtime supervision, Pydantic models, local package installation flow, Vue 3, existing plugin management UI

---

> 当前仓库约束：本计划不做旧插件兼容层；验证以 Python 编译检查、后端最小 API 自检、前端 `typecheck` 与 `build:check` 为主。

### Task 1: 建立 V2 插件协议与 SDK 模型

**Files:**
- Create: `squirrel-sdk/src/crawl/runtime_models.py`
- Create: `squirrel-sdk/src/crawl/runtime_protocol.py`
- Create: `squirrel-sdk/src/crawl/runtime_errors.py`
- Modify: `squirrel-sdk/src/crawl/__init__.py`
- Modify: `squirrel-sdk/src/crawl/plugin.py`

**Step 1: 定义 manifest 与 capability schema**

在 `runtime_models.py` 中定义：

- `PluginManifest`
- `PluginSiteManifest`
- `PluginCapability`
- `PluginPermission`
- `PluginHealthStatus`
- `PluginInvokeRequest`
- `PluginInvokeResponse`

要求：

- 字段命名稳定
- `sites` 和 `capabilities` 是一等数据
- 不再依赖旧 registry 反推站点信息

**Step 2: 定义 runtime 协议**

在 `runtime_protocol.py` 中定义 `PluginRuntime` Protocol，至少包含：

- `manifest()`
- `start(context)`
- `stop()`
- `health()`
- `invoke(capability, payload)`

**Step 3: 收敛错误模型**

在 `runtime_errors.py` 中定义标准错误码与错误 DTO，覆盖：

- timeout
- crashed
- bad response
- auth required
- network error
- parse error

**Step 4: 更新 SDK 导出面**

修改 `crawl/__init__.py` 与 `crawl/plugin.py`，让 V2 runtime API 成为主导出面，移除或弱化进程内 side-effect 注册路径。

**Step 5: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-sdk'
python -m compileall src
```

Expected: compile 成功

**Step 6: Commit**

```powershell
git add squirrel-sdk/src/crawl
git commit -m "feat: add plugin runtime v2 sdk contracts"
```

### Task 2: 搭建 backend V2 插件核心组件

**Files:**
- Create: `squirrel-backend/plugins/models.py`
- Create: `squirrel-backend/plugins/store.py`
- Create: `squirrel-backend/plugins/installer.py`
- Create: `squirrel-backend/plugins/supervisor.py`
- Create: `squirrel-backend/plugins/gateway.py`
- Create: `squirrel-backend/plugins/manager.py`

**Step 1: 建立宿主状态模型**

在 `models.py` 中定义：

- install record
- runtime status
- active version
- capability registration
- health snapshot

**Step 2: 建立插件安装记录持久层**

在 `store.py` 中落本地安装记录读写，至少保存：

- plugin id
- version
- install path
- enabled
- status
- granted permissions

**Step 3: 实现受控安装器**

在 `installer.py` 中实现：

- 包暂存
- manifest 校验
- entry point 校验
- 安装目录切换

**Step 4: 实现 runtime supervisor**

在 `supervisor.py` 中实现：

- 子进程启动
- 握手
- 心跳
- 停止
- 超时
- drain

**Step 5: 实现 capability gateway**

在 `gateway.py` 中实现：

- site/domain + capability 路由
- 请求/响应校验
- 插件异常标准化

**Step 6: 实现 PluginManager**

在 `manager.py` 中串起：

- discover
- install
- enable
- disable
- uninstall
- upgrade
- runtime snapshot

**Step 7: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall plugins
```

Expected: compile 成功

**Step 8: Commit**

```powershell
git add squirrel-backend/plugins
git commit -m "feat: add plugin runtime manager v2"
```

### Task 3: 替换启动与运行时装载链路

**Files:**
- Modify: `squirrel-backend/main.py`
- Modify: `squirrel-backend/processes/service_runtime.py`
- Modify: `squirrel-backend/plugins/reload_listener.py`
- Delete: `squirrel-backend/plugins/loader.py`
- Delete: `squirrel-backend/plugins/registry.py`
- Delete: `squirrel-backend/plugins/base.py`

**Step 1: 在 Web 启动链路接入 PluginManager**

把 `main.py` 从：

- `init_plugins()`
- `app_start()`
- `app_stop()`

切到 V2 的：

- manager bootstrap
- runtime start
- runtime shutdown

**Step 2: 在 worker/scheduler 启动链路接入 PluginManager**

修改 `service_runtime.py`，让独立进程共享同一套 V2 bootstrap。

**Step 3: 重写 reload 语义**

修改 `reload_listener.py`，把“reload”从模块清理改为 runtime refresh / version switch。

**Step 4: 删除旧主路径**

移除 `loader.py`、`registry.py`、`base.py` 的主路径职责，避免新旧并存。

**Step 5: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall main.py processes plugins
```

Expected: compile 成功

**Step 6: Commit**

```powershell
git add squirrel-backend/main.py squirrel-backend/processes/service_runtime.py squirrel-backend/plugins
git commit -m "refactor: bootstrap backend with plugin runtime manager"
```

### Task 4: 重做插件管理 API 与安装流程

**Files:**
- Modify: `squirrel-backend/services/plugin_service.py`
- Modify: `squirrel-backend/routes/plugins.py`

**Step 1: 重写插件服务层**

把 `plugin_service.py` 从目录扫描与 `plugins.json` 启停，改成基于 `PluginManager` 的：

- install
- enable
- disable
- uninstall
- list
- restart runtime

**Step 2: 重写插件路由返回模型**

调整 `/api/plugins` 系列接口返回：

- `plugin_id`
- `display_name`
- `version`
- `enabled`
- `status`
- `capabilities`
- `sites`
- `permissions`
- `health`
- `active_runtime`

**Step 3: 去掉旧来源语义**

删除 `internal/external/missing/package` 这类目录来源语义，不再让前端依赖目录结构。

**Step 4: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services routes
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/plugin_service.py squirrel-backend/routes/plugins.py
git commit -m "refactor: rebuild plugin management api for runtime v2"
```

### Task 5: 迁移一个最小示例插件跑通 V2

**Files:**
- Modify: `squirrel-plugins/bilibili/pyproject.toml`
- Create: `squirrel-plugins/bilibili/src/squirrel_bilibili/runtime.py`
- Modify: `squirrel-plugins/bilibili/src/squirrel_bilibili/__init__.py`

**Step 1: 调整 entry point 到 runtime 工厂**

把 bilibili 插件入口改成 V2 runtime 工厂，而不是模块级 side-effect 注册。

**Step 2: 实现最小 runtime**

在 `runtime.py` 中实现：

- manifest
- start
- stop
- health
- 至少一个 capability handler

**Step 3: 收敛插件导出面**

修改 `__init__.py`，移除对宿主侧 `plugins.registry` 的依赖。

**Step 4: 本地包构建检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-plugins\bilibili'
python -m build
```

Expected: 构建成功

**Step 5: Commit**

```powershell
git add squirrel-plugins/bilibili
git commit -m "refactor: migrate bilibili plugin to runtime v2"
```

### Task 6: 先迁低风险链路到 PluginGateway

**Files:**
- Modify: `squirrel-backend/services/site_login_status_service.py`
- Modify: `squirrel-backend/routes/plugins.py`
- Modify: `squirrel-backend/utils/site_catalog.py`

**Step 1: 登录检测改走 gateway**

把 `site_login_status_service.py` 从读取 login checker registry 改为调用 `check_login_status` capability。

**Step 2: 站点列表改读 manifest**

调整 `routes/plugins.py` 和 `site_catalog.py`，让 `/api/plugins/sites` 直接由 manifest 聚合：

- site name
- domains
- test url
- features

**Step 3: 保持连通性和 Cookie 入口不变**

接口路径先保持不变，只替换数据来源与能力调用路径。

**Step 4: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services routes utils
```

Expected: compile 成功

**Step 5: Commit**

```powershell
git add squirrel-backend/services/site_login_status_service.py squirrel-backend/routes/plugins.py squirrel-backend/utils/site_catalog.py
git commit -m "refactor: drive site metadata and login checks from plugin runtime"
```

### Task 7: 迁移主业务链路到 PluginGateway

**Files:**
- Modify: `squirrel-backend/services/video_service.py`
- Modify: `squirrel-backend/services/subscription_service.py`
- Modify: `squirrel-backend/core/extraction/factory.py`
- Modify: `squirrel-backend/queues/queue_config.py`

**Step 1: 视频播放链路改走 capability**

把 `video_service.py` 从 handler/proxy/subtitles registry 读取，改成：

- `resolve_playback`
- `fetch_subtitles`
- `proxy_stream`

**Step 2: 订阅导入链路改走 capability**

把 `subscription_service.py` 从 importer registry 读取，改成：

- `import_subscriptions`
- `sync_subscription`

**Step 3: 删除旧提取工厂主职责**

把 `core/extraction/factory.py` 降级为 gateway 适配器或直接移除站点实例缓存逻辑。

**Step 4: 队列站点映射改读 capability registry**

修改 `queue_config.py`，让域名到站点映射来自宿主 `CapabilityRegistry` 的快照，而不是 SDK extractor registry。

**Step 5: 编译检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall services core queues
```

Expected: compile 成功

**Step 6: Commit**

```powershell
git add squirrel-backend/services/video_service.py squirrel-backend/services/subscription_service.py squirrel-backend/core/extraction/factory.py squirrel-backend/queues/queue_config.py
git commit -m "refactor: route video and subscription flows through plugin gateway"
```

### Task 8: 重做前端插件管理页

**Files:**
- Modify: `squirrel-frontend/src/api/plugins.ts`
- Modify: `squirrel-frontend/src/views/PluginManager.vue`

**Step 1: 更新前端 API 类型与调用**

调整 `plugins.ts` 以匹配 V2 返回模型和新操作：

- restart runtime
- permissions
- health
- active runtime

**Step 2: 重构插件管理页信息结构**

让列表展示：

- 名称
- 版本
- 状态
- 权限
- capability 数
- site 数
- 健康状态

**Step 3: 移除目录来源视觉模型**

删除 “外部目录 / 内置插件 / 环境安装 / 配置缺失” 这类旧标签，改用统一 runtime 状态标签。

**Step 4: 保留站点运维入口**

保留连通性、Cookie、登录检测入口，但数据来源统一切到 manifest 和 gateway。

**Step 5: 前端检查**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run typecheck
npm run build:check
```

Expected: typecheck 与 build 通过

**Step 6: Commit**

```powershell
git add squirrel-frontend/src/api/plugins.ts squirrel-frontend/src/views/PluginManager.vue
git commit -m "refactor: rebuild plugin manager for runtime v2"
```

### Task 9: 删除旧 registry API 与补最终验证

**Files:**
- Modify: `squirrel-sdk/src/crawl/registry.py`
- Modify: `squirrel-sdk/src/crawl/registries.py`
- Modify: `squirrel-backend/README.md`
- Modify: `squirrel-plugins/README.md`

**Step 1: 删除或降级旧 registry API**

移除 V2 不再需要的宿主内 registry 主路径，避免新旧机制共存。

**Step 2: 更新文档**

更新 backend 与 plugins README，说明：

- 新插件包格式
- runtime 协议
- 安装与立即生效流程
- 不可信插件的权限模型

**Step 3: 全链路最小验证**

Run:

```powershell
Set-Location 'D:\Code\init\squirrel\squirrel-sdk'
python -m compileall src

Set-Location 'D:\Code\init\squirrel\squirrel-backend'
python -m compileall .

Set-Location 'D:\Code\init\squirrel\squirrel-frontend'
npm run build:check
```

Expected:

- SDK compile 成功
- backend compile 成功
- frontend build 成功
- 安装并启用最小示例插件后，`/api/plugins/` 与 `/api/plugins/sites` 可返回 V2 数据

**Step 4: Commit**

```powershell
git add squirrel-sdk/src/crawl squirrel-backend/README.md squirrel-plugins/README.md
git commit -m "refactor: finalize plugin runtime v2 migration"
```
