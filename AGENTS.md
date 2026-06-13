
## 项目结构

```
squirrel-backend/    Python/FastAPI 后端（核心项目）
squirrel-sdk/        Python SDK，stdlib-only，Protocol-based 接口
squirrel-site-runtimes/  站点插件（bilibili/youtube/pornhub/javdb/youporn）
squirrel-desktop/    Electron 桌面端，ESM 模块
squirrel-frontend/   Vue 3 前端（桌面端渲染进程）
squirrel-cf-bypass/  Cloudflare 绕过 sidecar
squirrel-music-api/  Node.js 音乐 API sidecar
squirrel-extension/  Chrome 扩展 MV3
```

## 构建与测试

### 后端 / SDK / 插件 / cf-bypass
```bash
pipenv install                    # 安装依赖
pipenv run pytest                 # 跑全部测试
pipenv run pytest path/to/test.py # 单文件
pipenv run pytest path/to/test.py::TestClass::test_method # 单用例
pipenv run ruff check             # lint（行长 120，E+F 规则）
```
- SDK 额外：`python -m compileall src; python -m build`
- 插件集成测试在 `squirrel-site-runtimes/tests/`（18 个文件）

### 桌面端
```bash
npm install                       # 安装依赖
npm run dev                       # 开发模式（前端 dev server + Electron）
node --test tests/<name>.test.mjs # 单测
```

### 前端（Vue 3，桌面端渲染进程）
```bash
npm install; npm run build:check  # 类型检查 + 构建
```
注意：前端是桌面端 Electron 的渲染进程，视频播放器等组件服务于桌面端。

## 代码约定

### Python（后端 / SDK / 插件）
- 单引号、snake_case、类型注解、f-string
- 导入：标准库 → 第三方 → 本地，分组空行
- DTO 用 dataclass，日志用 `logging.getLogger(__name__)`
- 插件异常映射：`NetworkError` / `AuthError` / `ParseError` / `RateLimitError` 等
- Docstring 全部用英文（Google-style）

### 桌面端（Electron）
- ESM 模块（`"type": "module"`）
- IPC 在 `src/ipc-handlers.mjs`，preload 暴露 `window.desktopApp`
- 播放解析在 `src/playback/providers/`，**不要绕到后端 `/api/video/url` 兜底**
- Cookie 在 `config/site_cookies/*.txt`（Netscape 格式）

### 前端（Vue 3）
- `<script setup>` + Pinia + Tailwind + CSS 变量
- API 调用用 `utils/request` + `handleRequest`/`ApiError`
- 播放器核心在 `src/components/video-player/core/`

