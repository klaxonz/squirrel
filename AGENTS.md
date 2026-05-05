# AGENTS

本文件用于指导在本仓库工作的智能编码代理。

## 范围
- 主要子项目：`squirrel-backend`、`squirrel-frontend`、`squirrel-desktop`、`squirrel-sdk`、`squirrel-plugins`。
- 辅助子项目：`squirrel-plugin-runner`、`squirrel-cf-bypass`、`squirrel-extension`。
- 修改应尽量限制在当前任务相关子项目；不要顺手格式化或重构无关代码。

## 构建、Lint、测试
### 后端（Python / FastAPI）
- 安装依赖：`pipenv install`（在 `squirrel-backend` 目录）。
- 本地运行通常依赖根目录 `.env.dev` 或 `.env`；不要修改真实凭据。
- Docker 运行：`docker compose up -d`（仓库根目录）。
- 测试：`pipenv run pytest`
- 单文件测试：`pipenv run pytest path/to/test_file.py`
- 单用例测试：`pipenv run pytest path/to/test_file.py::TestClass::test_name`

### 前端（Vue 3 + Vite）
- 安装依赖：`npm install`（在 `squirrel-frontend` 目录）。
- 开发服务器：`npm run dev`
- 生产构建：`npm run build`
- 类型检查：`npm run typecheck`
- 构建+类型检查：`npm run build:check`
- 前端不再维护、不新增、不运行测试。

### 桌面端（Electron）
- 安装依赖：`npm install`（在 `squirrel-desktop` 目录）。
- 开发运行：`npm run dev`（会拉起前端 dev server 并启动 Electron）。
- 仅启动桌面壳：`npm run start`（需要已存在可访问的 renderer URL）。
- 桌面构建：`npm run build`
- 安装包构建：`npm run dist`
- 桌面端测试使用 Node 内置 test runner，例如：`node --test tests/bilibili-provider.test.mjs`。

### SDK（Python 包）
- 安装依赖：`pipenv install`（在 `squirrel-sdk` 目录）或 `pip install -e .`。
- 构建 wheel/sdist：`python -m build`（需要安装 `build`）。
- 模块检查：`python -m compileall src`
- 当前仓库无 SDK 测试。

### 插件与运行器（Python）
- 每个插件位于 `squirrel-plugins/<site>/src/...`。
- 插件依赖 `squirrel-sdk` 的公开接口。
- `squirrel-plugin-runner` 是隔离插件运行桥接包，要求 Python 3.10+。
- 插件运行方式：随后端调度运行，或在 Python 中直接导入模块做针对性验证。

### Cloudflare Bypass Sidecar
- 子项目：`squirrel-cf-bypass`，要求 Python 3.11+。
- 依赖配置见 `squirrel-cf-bypass/pyproject.toml`。
- 作为本地/容器 sidecar 服务供后端调用，默认端口来自环境变量或 compose 配置。

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
- 配置入口：`squirrel-backend/core/config.py`（`pydantic_settings.BaseSettings`）。
- 统一使用 `Settings` 属性生成派生路径和 URL。
- Redis Stream 消息封装使用 `MqMessage`。
- 链路追踪使用 `utils/trace.py`。
- 并发：限速器使用按域名锁保证线程安全。
- API 鉴权以 `/api/users/login` 获取 cookie/session；不要在测试输出中打印密码。

### SDK 细则
- SDK 要求 Python 3.10+。
- 标注为 stdlib-only 的模块不要引入第三方依赖（见 `crawl/core.py`）。
- 公开 API 保持稳定，更新 `crawl/__init__.py` 与 `__all__`。
- 使用 `register_extractor` 装饰器或 `BaseExtractor` 自动注册。
- SDK 相关流程返回显式 `ExtractionResult`。

### 插件细则
- 插件类需提供 `site_name` 与 `supported_domains`。
- 解析逻辑尽量纯函数；网络调用集中封装。
- 将外部异常映射为 SDK 的错误类型（如 `NetworkError`、`AuthError`、`ParseError`）。
- 错误上下文以 dict 传入，便于排查。

### 前端（Vue）
- 使用 Vue 3 + Pinia + Vite；代码以 JS 为主，部分 composable 为 TS。
- 导入顺序：第三方 → 本地；相对路径保持一致。
- JS/TS 字符串使用单引号；缩进 2 个空格。
- Vue SFC 使用 `<script setup>`，状态与副作用逻辑集中放置。
- 组合式 API 使用 `ref`/`computed`/`watch`。
- API 调用使用 `utils/request` 与 `handleRequest`/`ApiError` 模式。
- 状态放在 `src/stores` 的 Pinia store。
- Tailwind 工具类大量使用；全局样式在 `src/styles`。
- 颜色优先使用 CSS 变量（如 `--bg-tertiary`）。
- 类型定义放在 `src/types` 或共享类型文件中。
- 前端改动不要求补充或更新测试。

### 视频播放与桌面端边界
- 桌面端是薄壳，但视频播放解析优先在桌面端完成。
- Bilibili/YouTube/Pornhub/YouPorn 等桌面播放解析位于 `squirrel-desktop/src/playback/providers`。
- 桌面端播放不要依赖后端 `/api/video/url` 作为兜底；若桌面 provider 失败，应修 provider、cookie、header 或 Electron bridge。
- 站点 cookie 存放于 `config/site_cookies/*.txt`，按 Netscape cookie 格式读取；不要打印完整 cookie 值。
- 前端播放器核心位于 `squirrel-frontend/src/components/video-player`，全局挂载在 `GlobalVideoPlayerHost.vue`。
- 列表进入播放页会使用 `videoPlaybackSeed` 传递视频快照；快照不能被当作可复用播放源。

### 桌面端（Electron）
- 主进程与 preload 使用 ESM。
- Node 与浏览器边界通过 preload/IPC 暴露，避免在渲染进程直接开启 Node 集成。
- `DESKTOP_RENDERER_URL` 指向前端页面；`DESKTOP_APP_URL` 指向后端服务地址。
- 本地自动化验证可用 Playwright Electron，但要注意单实例锁；必要时先关闭已有 Electron 进程。

## 仓库说明
- Docker Compose 支持全量部署；参考根目录 `docker-compose.yaml`。
- backend/worker/scheduler 使用同一镜像。
- 配置文件位于 `config/` 并挂载进容器。
- Cookie 存放于 `config/site_cookies`。
- 避免编辑 `plugin_packages/*.zip`、`dist/`、`release/` 等产物。

## 推荐工作流
### 后端快速流程
1. `pipenv install`
2. `pipenv run pytest` 或精准测试相关文件

### 前端快速流程
1. `npm install`
2. `npm run typecheck`
3. `npm run build` 或 `npm run build:check`

### 桌面端快速流程
1. `npm install`
2. `npm run dev` 或先启动前端再 `npm run start`
3. `node --test tests/<related>.test.mjs`
4. 必要时用 Electron 真机验证播放/窗口行为

### SDK 快速流程
1. `pip install -e .`
2. `python -m compileall src`
3. `python -m build`

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
