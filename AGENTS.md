# AGENTS

本文件用于指导在本仓库工作的智能编码代理。

## 范围
- 主要子项目：`squirrel-backend`、`squirrel-frontend`、`squirrel-desktop`、`squirrel-sdk`、`squirrel-site-runtimes`。
- 辅助子项目：`squirrel-cf-bypass`、`squirrel-music-api`、`squirrel-extension`。
- 修改应尽量限制在当前任务相关子项目；不要顺手格式化或重构无关代码。

## 构建、Lint、测试

### 后端（Python / FastAPI）
- 依赖管理：`pipenv install`（在 `squirrel-backend` 目录）。
- 本地运行通常依赖根目录 `.env.dev` 或 `.env`；不要修改真实凭据。
- Docker 运行：`docker compose up -d`。
- 测试：`pipenv run pytest`
- 单文件测试：`pipenv run pytest path/to/test_file.py`
- 单用例测试：`pipenv run pytest path/to/test_file.py::TestClass::test_name`
- Lint：使用 Ruff，配置在 `pyproject.toml`（规则 E + F，忽略 E501，行长度 120，目标 py38，圈复杂度 ≤10）。
- 数据库迁移：Alembic，迁移文件位于 `alembic/versions/`。

### 前端（Vue 3 + Vite）
- 依赖安装：`npm install`（在 `squirrel-frontend` 目录）。
- 开发服务器：`npm run dev`
- 生产构建：`npm run build`
- 类型检查：`npm run typecheck`
- 构建+类型检查：`npm run build:check`
- 前端不再维护、不新增、不运行测试。

### 桌面端（Electron）
- 依赖安装：`npm install`（在 `squirrel-desktop` 目录，`"type": "module"`）。
- 开发运行：`npm run dev`（会拉起前端 dev server 并启动 Electron）。
- 仅启动桌面壳：`npm run start`（需要已存在可访问的 renderer URL）。
- 桌面构建：`npm run build`
- 安装包构建：`npm run dist`（目标：Windows NSIS installer + portable）。
- 测试使用 Node 内置 test runner：`node --test tests/<name>.test.mjs`
- 可用测试文件：`bilibili-provider.test.mjs`、`youtube-provider.test.mjs`、`javdb-provider.test.mjs`、`adult-providers.test.mjs`、`remote-search-providers.test.mjs`、`site-login.test.mjs`、`window-state.test.mjs`。

### SDK（Python 包）
- 依赖安装：`pipenv install` 或 `pip install -e .`（在 `squirrel-sdk` 目录）。
- 构建 wheel/sdist：`python -m build`
- 模块检查：`python -m compileall src`
- 测试：`pipenv run pytest`（当前仅有 `tests/test_http.py`）。
- 需要 Python ≥ 3.10。

### 插件（Site Runtimes）
- 每个插件位于 `squirrel-site-runtimes/<site>/` 目录。
- 插件依赖 `squirrel-sdk` 的公开接口，安装 wheel 后自动注册。
- 插件使用 `squirrel.site_runtimes` entry point 组注册。
- 每个插件有独立 `pyproject.toml`，入口统一为 `runtime.py:get_site_runtime`。
- 集成测试位于 `squirrel-site-runtimes/tests/`（18 个测试文件）。
- 运行测试：`pipenv run pytest`（从 `squirrel-site-runtimes` 目录）。
- 当前插件列表：

| 站点 | 包名 | pyproject.toml 入口 | 关键依赖 |
|------|------|---------------------|---------|
| bilibili | squirrel-plugin-bilibili v0.1.0 | `squirrel_bilibili.runtime:get_site_runtime` | yt-dlp |
| youtube | squirrel-plugin-youtube v0.1.0 | `squirrel_youtube.runtime:get_site_runtime` | beautifulsoup4, pytubefix, yt-dlp, httpx, fastapi |
| pornhub | squirrel-plugin-pornhub v0.1.0 | `squirrel_pornhub.runtime:get_site_runtime` | beautifulsoup4, yt-dlp, phub, httpx, fastapi |
| javdb | squirrel-plugin-javdb v0.1.0 | `squirrel_javdb.runtime:get_site_runtime` | beautifulsoup4, httpx, fastapi |
| youporn | squirrel-plugin-youporn v0.1.0 | `squirrel_youporn.runtime:get_site_runtime` | beautifulsoup4, yt-dlp, httpx, fastapi |

### Cloudflare Bypass Sidecar
- 子项目：`squirrel-cf-bypass`，要求 Python 3.11+。
- 依赖配置见 `pyproject.toml`：fastapi, curl-cffi, camoufox, httpx, playwright-captcha 等。
- 作为本地/容器 sidecar 服务供后端调用，默认端口 8002。
- Dockerfile 基于 python:3.11-slim，CMD 为 `uvicorn squirrel_cf_bypass.app.main:app`。
- 测试：`pipenv run pytest`（5 个测试文件）。

### 音乐 API Sidecar
- 子项目：`squirrel-music-api`，Node.js 应用。
- 基于 `kugoumusicapi` 包，端口 8003。
- Dockerfile 基于 node:20-alpine。
- 运行方式：Docker 或直接 `npm run start`。

### 浏览器扩展
- 子项目：`squirrel-extension`，Chrome Manifest V3。
- 文件：`manifest.json`、`background.js`、`popup.html/js`、`options.html/js`、`config.js`、`utils.js`。

## 代码风格与约定

### 通用要求
- 与用户沟通使用中文。
- 代码注释与日志内容必须使用英文。
- 优先写小而清晰的函数，保持数据流清晰。
- 避免触碰生成文件：`dist`、`release`、`__pycache__`、`.pytest_cache`、`.ruff_cache`、`node_modules`。
- 不要提交密钥；本地存在 `.env`、`.env.dev`、`.env.test` 文件。
- 用户已有未提交改动时，必须避免覆盖；先看 `git diff`/`git status`。

### Python（后端、SDK、插件）
- 导入顺序：标准库 → 第三方 → 本地；分组之间空行。
- 命名规范：函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE`。
- 类型：使用类型注解；DTO 常用 dataclass。
- 日志：使用 `logging.getLogger(__name__)` 或模块级 logger，日志文本保持英文。
- 字符串：优先单引号；字符串插值使用 f-string。
- 行长度：120（ruff 配置）。
- 异常处理：只在边界捕获广泛异常；必要时转换为领域错误类型。

### 后端细则
- 配置入口：`core/config.py`（`pydantic_settings.BaseSettings`，`@lru_cache` 单例）。
- 统一使用 `Settings` 属性生成派生路径和 URL。
- Redis Stream 消息封装使用 `MqMessage`（`queues/message.py`）。
- 链路追踪使用 `utils/trace.py`（ContextVar-based `trace_id`）。
- 并发：限速器使用按域名锁保证线程安全。
- API 鉴权以 `/api/users/login` 获取 cookie/session；不要在测试输出中打印密码。
- App 创建入口：`routes/base.py` 的 `create_app()`，挂载中间件（auth、CORS、access log、trace）和所有路由。
- 数据库：SQLAlchemy + PostgreSQL，Alembic 迁移。
- 后台进程：`processes/worker_process.py`（worker）、`processes/scheduler_process.py`（调度器）。
- 提取管道：`core/extraction/` —— adapters、handlers、pipeline、services、task_manager。
- 站点运行时管理器：`site_runtimes/` —— gateway、health、manager、process_launcher、supervisor、runtime_bridge。
- 不要修改 `site_runtimes/` 目录下的 *.py 文件，除非是专门负责该模块的任务。

### SDK 细则
- SDK 要求 Python 3.10+。
- 标注为 stdlib-only 的模块不要引入第三方依赖（见 `crawl/core.py`）。
- 公开 API 保持稳定，更新 `crawl/__init__.py` 与 `__all__`（约 60 个导出项）。
- 使用 Runtime V2 设计：Protocol-based 接口（structural typing）、VideoMeta 为主要模型、组合优于继承。
- 关键类型：`ExtractionTask`、`ExtractionResult`、`VideoMeta`、`ActorMeta`、`Subscription`、`SubscriptionSyncResult`、`Extractor`、`TaskProcessor`、`ResultHandler`、`UserSubscriptionImporter`、`PaginatedUserSubscriptionImporter`。
- 错误类型：`ErrorCategory`、`PluginError`、`NetworkError`、`RateLimitError`、`AuthError`、`VipError`、`NotFoundError`、`ParseError`、`NoSubtitlesError`。
- SDK 相关流程返回显式 `ExtractionResult`。

### 插件细则
- 插件类需提供 `site_name` 与 `supported_domains`。
- 解析逻辑尽量采用纯函数；网络调用集中封装。
- 将外部异常映射为 SDK 的错误类型（如 `NetworkError`、`AuthError`、`ParseError`）。
- 错误上下文以 dict 传入，便于排查。
- 插件入口统一为 `runtime.py` 中的 `get_site_runtime()` 函数。

### 前端（Vue）
- 使用 Vue 3 + Pinia + Vite + TypeScript；代码以 JS 为主，部分 composable 为 TS。
- 导入顺序：第三方 → 本地；相对路径保持一致。
- JS/TS 字符串使用单引号；缩进 2 个空格。
- Vue SFC 使用 `<script setup>`，状态与副作用逻辑集中放置。
- 组合式 API 使用 `ref`/`computed`/`watch`。
- API 调用使用 `utils/request` 与 `handleRequest`/`ApiError` 模式。
- 状态放在 `src/stores` 的 Pinia store（`player.ts`、`user.ts`、`theme.ts`、`ui.ts`、`musicPlayer.ts`）。
- Tailwind 工具类大量使用；全局样式在 `src/styles`。
- 颜色优先使用 CSS 变量（如 `--bg-tertiary`）。
- 类型定义放在 `src/types` 或共享类型文件中。
- 前端改动不要求补充或更新测试。
- 播放器核心位于 `src/components/video-player/core/`，支持插件系统、事件总线、多适配器（BackendPlayerAdapter）。

### 视频播放与桌面端边界
- 桌面端是薄壳，但视频播放解析优先在桌面端完成。
- Bilibili/YouTube/Pornhub/YouPorn/JavDB 等桌面播放解析位于 `squirrel-desktop/src/playback/providers`。
- 桌面端播放不要依赖后端 `/api/video/url` 作为兜底；若桌面 provider 失败，应修 provider、cookie、header 或 Electron bridge。
- 站点 cookie 存放于 `config/site_cookies/*.txt`，按 Netscape cookie 格式读取；不要打印完整 cookie 值。
- 前端播放器核心位于 `squirrel-frontend/src/components/video-player`，全局挂载在 `GlobalVideoPlayerHost.vue`。
- 列表进入播放页会使用 `videoPlaybackSeed` 传递视频快照；快照不能被当作可复用播放源。

### 桌面端（Electron）
- 主进程使用 ESM（`"type": "module"`），preload 同时提供 CommonJS（`preload.cjs`）和 ESM（`preload.mjs`）变体。
- Node 与浏览器边界通过 preload/IPC 暴露，避免在渲染进程直接开启 Node 集成。
- `DESKTOP_RENDERER_URL` 指向前端页面；`DESKTOP_APP_URL` 指向后端服务地址。
- IPC 处理器集中在 `src/ipc-handlers.mjs`，通过 `window.desktopApp` 桥接暴露给渲染进程。
- 支持 API：播放解析（YouTube、Bilibili、Pornhub、YouPorn、JavDB）、远程搜索、站点登录、窗口控制、服务器 URL 配置。
- 本地自动化验证可用 Playwright Electron，但要注意单实例锁；必要时先关闭已有 Electron 进程。
- Camoufox 用于站点登录自动化，通过 `npm run fetch:camoufox` 下载。

## 仓库概览

### Docker Compose
`docker-compose.yaml` 定义 7 个服务：

| 服务 | 镜像 | 端口 | 命令 | 健康检查 |
|------|------|------|------|---------|
| squirrel-music-api | klaxonz/squirrel-music-api | 8003:3000 | npm start | HTTP /register/dev |
| squirrel-cf-bypass | klaxonz/squirrel-cf-bypass | 8002:8002 | uvicorn | HTTP /health |
| squirrel | klaxonz/squirrel | 8001:8001 | `python main.py` | HTTP /health |
| squirrel-worker | klaxonz/squirrel | - | `python -m processes.worker_process` | 无 |
| squirrel-scheduler | klaxonz/squirrel | - | `python -m processes.scheduler_process` | 无 |
| redis | redis:7-alpine | 6379 | 需密码 | redis-cli ping |
| postgres | postgres:15-alpine | 5432 | 默认 | pg_isready |

全量部署：`docker compose up -d`
standalone 部署：`docker compose up -d --no-deps squirrel squirrel-worker squirrel-scheduler`

### 构建系统（Dockerfile）
- 多阶段构建：frontend-builder（Vue）→ youtube-node-builder → python-builder（Pipfile + SDK + site-runtime wheels）→ final。
- 基础镜像：`ghcr.io/klaxonz/squirrel-base`（Python 3.11-slim + Chromium + Node.js 20 + ffmpeg）。

### 配置文件
- 根目录：`.env.dev`、`.env.test`、`env.example`。
- `config/sites.json` —— 站点配置（域名、别名、HTTP 头、登录配置、代理、限速、元数据）。
- `config/youtube_oauth.json` —— YouTube OAuth 凭据。
- `config/site_cookies/` —— Netscape 格式 cookie 文件，每个站点一个 `.txt` 文件加 `.lock` 文件。

### 产物目录
- 避免编辑：`dist/`、`release/`、`__pycache__`、`.pytest_cache`、`.ruff_cache`、`node_modules`。
- 避免编辑：`squirrel-backend/plugin_packages/*.zip`。
- Docker Compose 会挂载 `./config:/app/config`、`./logs:/app/logs`、`./downloads:/downloads`。

## 推荐工作流

### 后端快速流程
1. `pipenv install`（在 `squirrel-backend` 目录）
2. `pipenv run pytest` 或精准测试相关文件

### 前端快速流程
1. `npm install`（在 `squirrel-frontend` 目录）
2. `npm run typecheck`
3. `npm run build` 或 `npm run build:check`

### 桌面端快速流程
1. `npm install`（在 `squirrel-desktop` 目录）
2. `npm run dev` 或先启动前端再 `npm run start`
3. `node --test tests/<related>.test.mjs`
4. 必要时用 Electron 真机验证播放/窗口行为

### SDK 快速流程
1. `pip install -e .`（在 `squirrel-sdk` 目录）
2. `python -m compileall src`
3. `python -m build`

### 插件（Site Runtimes）快速流程
1. `pip install -e .`（在插件目录或 SDK 目录）
2. `pipenv run pytest`（从 `squirrel-site-runtimes` 目录运行集成测试）
3. 或直接 `python -c "from <module> import ..."` 针对性验证

## 可做与不可做
- 可做：保持行为变更最小化并记录。
- 可做：遵循现有模块边界与命名模式。
- 可做：若命令、脚本或验证方式变更，更新本文件。
- 不可做：修改 `.env` 或凭据。
- 不可做：格式化不相关代码。
- 不可做：把桌面播放问题绕到后端接口兜底。

## 规则
- 本仓库未发现 Cursor 规则（`.cursor/rules/` 或 `.cursorrules`）。
- 本仓库未发现 Copilot 规则（`.github/copilot-instructions.md`）。
- 若新增规则，需要同步更新本文件。
