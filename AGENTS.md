# Squirrel — 智能编码助手指引

## 开发流程

**硬规则：任何涉及代码、配置或仓库规则变更的任务，必须先判断任务类型并 load 对应 skill。不要只按触发词判断。**

### 新功能 / 行为变更（feature-flow skill）

新增能力、调整既有行为、跨模块改造，使用 `feature-flow` skill，从需求到代码合入全链路：

0. **需求获取** → 用 template 创建 `.workflow/requirements/req-<name>.md`，用户确认
1. **需求理解** → 确认范围、子项目、红线
2. **设计方案** → 调研代码，输出方案到 `.workflow/designs/des-feature-<name>.md`，用户确认后开干
3. **编码实现** → 按设计方案实现，涉及范围内可做最佳实践重构
4. **审查** → 对照设计方案逐条覆盖
5. **测试** → lint + 类型检查 + 相关测试
6. **收尾** → 更新文档状态，报告改动，问 commit

### 缺陷 / 启动失败 / 测试失败（code-fix skill）

报错日志、traceback、启动失败、运行时异常、测试失败、回归问题，使用 `code-fix` skill：

1. 先创建或定位 `.workflow/issues/issue-<NNN>-<title>.md`
2. 调研根因，输出 `.workflow/designs/des-fix-<issue-id>-<title>.md`
3. 对局部低风险修复可直接实施；涉及跨模块、公共接口、数据迁移、权限/安全逻辑或行为兼容性变化时，先让用户确认方案
4. 验证后关闭 issue，并在设计文档记录验证结果

### 纯文档 / 指引调整

只修改 README、AGENTS、workflow 文档或说明文字时，不强制创建需求/设计文档；但仍必须先检查 `git status`，只改相关文件，并在最终回复说明未运行代码测试或说明验证方式。

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

## 关键限制（红线）
| 规则 | 说明 |
|------|------|
| 不改 `site_runtimes/` 下的 .py 文件 | 除非专门分配了该模块任务 |
| 不改 .env / 凭据 | 本地有 `.env.dev` / `.env.test` |
| 桌面播放问题不上后端兜底 | 修 provider 本身 |
| 不改未涉及子项目的代码 | 不顺手格式化无关代码，涉及范围内可做最佳实践重构 |
| 已有未提交改动先看 `git diff`/`git status` | 避免覆盖 |

## 文档工作流
| 命令 | 用途 | 存储位置 |
|------|------|---------|
| `/req <name>` | 创建需求文档 | `.workflow/requirements/req-<name>.md` |
| `/design <name>` | 创建技术方案 | `.workflow/designs/des-feature-<name>.md`（有对应需求时，name 必须与需求一致） |
| `/bug <title>` | 报告缺陷（status=open） | `.workflow/issues/issue-<NNN>-<title>.md`（NNN 取目前最大序号 +1） |
| `/issues` | 列出所有 open 的 issue | — |
| `/issue close <name>` | 关闭 issue（status→fixed） | `.workflow/issues/<name>.md`（传入文件名去除 `.md` 后缀的部分） |
| `/issue reopen <name>` | 重新打开 issue（status→open） | 同上 |

**命名关联规则：** 同一特性的需求、设计、Issue 使用相同 `<name>`，详见 feature-flow skill 的「文档命名约定」。

## 项目记忆
<!-- 使用 /remember 添加记忆，/recall 搜索记忆 -->
