# Squirrel — 智能编码助手指引

## 开发流程

1. **需求** → 读 `.opencode/requirements/<name>.md` 理解需求，或用 `/req` 新建
2. **设计** → 输出技术方案到 `.opencode/designs/<name>.md`，或用 `/design` 新建
3. **实现** → 按设计方案编码，保持变更最小化
4. **审查** → 对照设计方案 review 代码
5. **测试** → 按验收标准验证

## 项目结构

```
squirrel-backend/    Python/FastAPI 后端（核心项目）
squirrel-sdk/        Python SDK，stdlib-only，Protocol-based 接口
squirrel-site-runtimes/  站点插件（bilibili/youtube/pornhub/javdb/youporn）
squirrel-desktop/    Electron 桌面端，ESM 模块
squirrel-frontend/   Vue 3 前端（不再维护，不新增功能）
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
pipenv run pytest::TestClass::test_method # 单用例
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

### 前端
```bash
npm install; npm run build:check  # 类型检查 + 构建
```
⚠️ 前端不再维护，不新增功能，不要求测试。

## 代码约定

### Python（后端 / SDK / 插件）
- 单引号、snake_case、类型注解、f-string
- 导入：标准库 → 第三方 → 本地，分组空行
- DTO 用 dataclass，日志用 `logging.getLogger(__name__)`
- 插件异常映射：`NetworkError` / `AuthError` / `ParseError` / `RateLimitError` 等

### 桌面端（Electron）
- ESM 模块（`"type": "module"`）
- IPC 在 `src/ipc-handlers.mjs`，preload 暴露 `window.desktopApp`
- 播放解析在 `src/playback/providers/`，**不要绕到后端 `/api/video/url` 兜底**
- Cookie 在 `config/site_cookies/*.txt`（Netscape 格式）

### 前端（Vue 3）
- `<script setup>` + Pinia + Tailwind + CSS 变量
- API 调用用 `utils/request` + `handleRequest`/`ApiError`
- 播放器核心在 `src/components/video-player/core/`

## 关键限制（红线）
| 规则 | 说明 |
|------|------|
| 不改 `site_runtimes/` 下的 .py 文件 | 除非专门分配了该模块任务 |
| 不改 .env / 凭据 | 本地有 `.env.dev` / `.env.test` |
| 桌面播放问题不上后端兜底 | 修 provider 本身 |
| 不改未涉及子项目的代码 | 不顺手格式化/重构 |
| 已有未提交改动先看 `git diff`/`git status` | 避免覆盖 |

## 文档工作流
| 命令 | 用途 | 存储位置 |
|------|------|---------|
| `/req <name>` | 创建需求文档 | `.opencode/requirements/<name>.md` |
| `/design <name>` | 创建技术方案 | `.opencode/designs/<name>.md` |
| `/bug <title>` | 报告缺陷 | `.opencode/issues/<title>.md` |

## 项目记忆
<!-- 使用 /remember 添加记忆，/recall 搜索记忆 -->

