# AGENTS

本文件用于指导在本仓库工作的智能编码代理。

## 范围
- 主要子项目：`squirrel-backend`、`squirrel-frontend`、`squirrel-desktop`、`squirrel-sdk`、`squirrel-plugins`。

## 构建、Lint、测试
### 后端（Python / FastAPI）
- 安装依赖：`pipenv install`（在 `squirrel-backend` 目录）。
- 使用 Docker 运行：`docker compose up -d`（仓库根目录）。
- 测试（可选）：`pipenv run pytest`
- 单个测试文件（可选）：`pipenv run pytest path/to/test_file.py`
- 单个测试用例（可选）：`pipenv run pytest path/to/test_file.py::TestClass::test_name`

### SDK（Python 包）
- 安装依赖：`pipenv install`（在 `squirrel-sdk` 目录）或 `pip install -e .`
- 构建 wheel/sdist：`python -m build`（需要安装 `build`）
- 模块检查：`python -m compileall src`
- 测试：当前仓库无 SDK 测试。

### 前端（Vue 3 + Vite）
- 安装依赖：`npm install`（在 `squirrel-frontend` 目录）。
- 开发服务器：`npm run dev`
- 生产构建：`npm run build`
- 类型检查：`npm run typecheck`
- 构建+类型检查：`npm run build:check`
- 测试：当前仓库未配置前端测试。

### 桌面端（Electron）
- 安装依赖：`npm install`（在 `squirrel-desktop` 目录）。
- 开发运行：`npm run dev`
- 本地启动：`npm run start`
- 桌面构建：`npm run build`
- 安装包构建：`npm run dist`

### 插件（Python）
- 每个插件位于 `squirrel-plugins/<site>/src/...`。
- 插件依赖 `squirrel-sdk` 的接口。
- 插件运行方式：随后台运行或在 Python 中直接导入模块。

## 代码风格与约定
### 通用要求
- 与用户沟通使用中文。
- 代码注释与日志内容必须使用英文。
- 优先写小而清晰的函数，保持数据流清晰。
- 修改范围应限制在当前子项目。
- 避免触碰生成文件（如 `dist`、`__pycache__`）。
- 不要提交密钥；本地存在 `.env` 文件。

### Python（后端、SDK、插件）
- Python 版本：后端以项目实际依赖为准；SDK 要求 3.10+。
- 导入顺序：标准库 → 第三方 → 本地；分组之间空行。
- 命名规范：函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE`。
- 类型：使用类型注解；DTO 常用 dataclass。
- 接口：SDK 使用 `typing.Protocol` 进行结构化类型约束。
- 错误：插件侧优先抛出 SDK 的 `PluginError` 子类（network/auth/parse 等）。
- 日志：使用 `logging.getLogger(__name__)` 或模块级 logger，日志文本保持英文。
- 字符串：优先单引号；字符串插值使用 f-string。
- 行长度：120（ruff 配置）。
- 异常处理：只在边界捕获广泛异常；必要时转换为 `PluginError`。
- 结果：SDK 相关流程返回显式 `ExtractionResult`。

### 后端细则
- 配置入口：`squirrel-backend/core/config.py`（`pydantic_settings.BaseSettings`）。
- 统一使用 `Settings` 属性生成派生路径和 URL。
- Redis Stream 消息封装使用 `MqMessage`。
- 链路追踪使用 `utils/trace.py`。
- 并发：限速器使用按域名锁保证线程安全。

### SDK 细则
- 标注为 stdlib-only 的模块不要引入第三方依赖（见 `crawl/core.py`）。
- 公开 API 保持稳定，更新 `crawl/__init__.py` 与 `__all__`。
- 使用 `register_extractor` 装饰器或 `BaseExtractor` 自动注册。

### 插件细则
- 插件类需提供 `site_name` 与 `supported_domains`。
- 解析逻辑尽量纯函数；网络调用集中封装。
- 将外部异常映射为 SDK 的错误类型（`NetworkError`、`AuthError` 等）。
- 错误上下文以 dict 传入，便于排查。

### 前端（Vue）
- 使用 Vue 3 + Pinia + Vite；代码以 JS 为主，部分 composable 为 TS。
- 导入顺序：第三方 → 本地；相对路径保持一致。
- JS/TS 字符串使用单引号。
- 缩进：2 个空格。
- Vue SFC 使用 `<script setup>`，状态与副作用逻辑集中放置。
- 组合式 API 使用 `ref`/`computed`/`watch`。
- API 调用使用 `utils/request.js` 与 `handleRequest`/`ApiError`。
- 状态放在 `src/stores` 的 Pinia store。
- Tailwind 工具类大量使用；全局样式在 `src/styles`。
- 颜色优先使用 CSS 变量（如 `--bg-tertiary`）。
- 类型定义在 `src/types` 或共享类型文件中。

### 桌面端（Electron）
- 主进程与 preload 使用 ESM。
- 保持桌面端为薄壳，优先加载现有 Web UI，不复制页面逻辑。
- Node 与浏览器边界通过 preload 暴露，避免在渲染进程直接开启 Node 集成。

### 错误处理模式
- 后端：日志记录上下文后再抛出或返回安全默认值。
- SDK/插件：抛出 `PluginError` 子类以分类错误。
- 前端：`handleRequest` 返回 `{ data, error }` 并显示用户可读信息。

## 仓库说明
- Docker Compose 支持全量部署；参考根目录 `docker-compose.yaml`。
- backend/worker/scheduler 使用同一镜像。
- 配置文件位于 `config/` 并挂载进容器。
- Cookie 存放于 `config/site_cookies`。
- 避免编辑 `plugin_packages/*.zip` 或 `dist/` 产物。

## 推荐工作流
### 后端快速流程
1) `pipenv install`
2) （可选）`pipenv run pytest`（如果存在测试）

### 前端快速流程
1) `npm install`
2) `npm run typecheck`
3) `npm run build`

### 桌面端快速流程
1) `npm install`
2) `npm run build`

### SDK 快速流程
1) `pip install -e .`
2) `python -m build`

## 可做与不可做
- 可做：保持行为变更最小化并记录。
- 可做：遵循现有模块边界与命名模式。
- 可做：若命令变更，更新本文件。
- 不可做：修改 `.env` 或凭据。
- 不可做：格式化不相关代码。

## 已知配置
- 前端脚本：`squirrel-frontend/package.json`。
- SDK 构建配置：`squirrel-sdk/pyproject.toml`。

## 若新增工具
- 将脚本加入就近的 `package.json` 或 `Pipfile`。
- 在本文件中补充新命令。
- 配置尽量局部化，放在对应子项目。

## 规则
- 本仓库未发现 Cursor 规则（`.cursor/rules/` 或 `.cursorrules`）。
- 本仓库未发现 Copilot 规则（`.github/copilot-instructions.md`）。
- 若新增规则，需要同步更新本文件。

## 结尾
- 本文件保持约 150 行，便于快速浏览。
