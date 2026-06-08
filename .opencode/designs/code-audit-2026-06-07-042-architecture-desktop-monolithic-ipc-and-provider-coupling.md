# Desktop 架构修复：IPC 拆分 + main.mjs 解耦 + file-cache 迁移

## 根因

桌面端 IPC 处理、provider 预热、缓存基础设施的代码组织没有随功能增长演进，导致单体文件和紧耦合。

## 修复思路（4 项）

### 1. 拆分 `ipc-handlers.mjs`

按领域拆为 5 个文件，每个文件导出 `installXxxHandlers()`，`ipc-handlers.mjs` 作为入口统一调用：

| 新文件 | 搬运的 IPC 通道 |
|--------|----------------|
| `ipc-playback.mjs` | `desktop:resolve-{youtube,bilibili,pornhub,javdb,youporn}-{playback,subtitles,metadata}` |
| `ipc-search.mjs` | `desktop:search-remote-videos`, `desktop:get-remote-channel`, `desktop:get-youporn-profile-avatar` |
| `ipc-window.mjs` | `desktop:open-external`, `desktop:reload`, `desktop:get-window-state`, `desktop:window-action` |
| `ipc-site-login.mjs` | `desktop:get-site-login-status`, `desktop:open-site-login`, `desktop:clear-site-session` |
| `ipc-server-config.mjs` | `server:get-url`, `server:set-url`, `server:clear-url` |

`ipc-handlers.mjs` 精简为 ~20 行入口，依次调用各子模块的 install 函数。

### 2. 解耦 `main.mjs` 与 YouTube provider

创建 `playback/providers/index.mjs` 注册所有 playback provider，提供 `prewarmPlaybackProviders()` — 遍历各 provider 若有 prewarm 则调用。main.mjs 只引用 registry，不再直接 import YouTube。

### 3. 统一 provider 导出

- javdb 的 `__testing` 从 index.mjs 移到内部分文件 `javdb/__testing.mjs`
- javdb/index.mjs 不再 export `__testing`
- 测试文件更新 import 路径

### 4. `file-cache.mjs` → `shared/`

从 `playback/file-cache.mjs` 移到 `shared/file-cache.mjs`，更新所有 import。

## 涉及文件

| 文件 | 操作 |
|------|------|
| `src/ipc-handlers.mjs` | 精简为入口 |
| `src/ipc-playback.mjs` | 新建 |
| `src/ipc-search.mjs` | 新建 |
| `src/ipc-window.mjs` | 新建 |
| `src/ipc-site-login.mjs` | 新建 |
| `src/ipc-server-config.mjs` | 新建 |
| `src/main.mjs` | 改 import + prewarm 逻辑 |
| `src/playback/providers/index.mjs` | 新建 |
| `src/playback/file-cache.mjs` | 移到 `src/shared/file-cache.mjs` |
| `src/shared/file-cache.mjs` | 新建（from playback/） |
| `src/playback/providers/shared/playback-cache.mjs` | 更新 import path |
| `src/playback/providers/javdb/index.mjs` | 移除 `__testing` export |
| `src/playback/providers/javdb/__testing.mjs` | 新建 |
| `tests/javdb-provider.test.mjs` | 更新 import path |
| `preload.mjs` | 无变更（IPC 通道名不变） |

## 潜在风险

- **IPC 通道名不变** → preload 和前端不感知，零风险
- **file-cache 移动** → 只有 `playback-cache.mjs` 引用它，精确替换即可
- **javdb __testing** → 只在单测中使用，更新 import 路径即可
- **provider registry** → 只影响 prewarm 逻辑，不影响 playback resolve
- 后端 / SDK / 插件 / 前端均不受影响
