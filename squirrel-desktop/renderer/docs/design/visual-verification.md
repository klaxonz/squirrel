# Visual Verification（桌面端 · Electron + CDP）

← [UI Clone Anchors](./ui-clone-anchors.md) · [Governance](./governance.md)

## 结论

Squirrel 是 **Electron 桌面应用**，不是纯 Web。
视觉与功能验证的默认路径必须是：

**真实 Electron 进程 + CDP（Playwright `_electron`）**

这样才有：

- `window.desktopApp` / preload `contextBridge`
- 主进程 IPC（播流解析、站点登录、音乐、远端搜索…）
- 自定义标题栏、窗口状态、媒体请求头
- 与用户实际使用路径一致的渲染进程

| 驱动 | 何时用 | 能力 |
|------|--------|------|
| **`electron`（默认）** | 布局合入、桌面能力相关 | 完整桌面壳 + IPC |
| **`browser`（可选）** | 仅快速探针 CSS/布局、无桌面桥 | **无** preload/IPC；**不能**代替桌面验收 |

> 历史：曾用独立 Chromium 截 Vite，只能验 DOM/CSS，**无法**覆盖桌面功能。
> 现已改为默认 Electron。旧 browser baseline 与 Electron 截图不可混比，需 `visual:update` 重建一次。

---

## 原理

```text
npm run visual:*
  → 探测 Squirrel Vite（DESKTOP_RENDERER_URL）
  → playwright-core._electron.launch(electron.exe, cwd=squirrel-desktop)
       env: SQUIRREL_VISUAL_TEST=1  （隔离 userData + 跳过单实例锁）
  → firstWindow() 拿到 CDP Page
  → 断言 window.desktopApp.isDesktop === true
  → 登录（.env.dev DEV_AUTH_*）
  → 每个场景：
       hash 导航（不 reload，避免丢 hash）
       → 等 hash 路由匹配
       → 等 .app-layout 壳就绪（workspace 有尺寸）
       → 等 XHR/fetch 安静 ~800ms
       → 等布局签名连续稳定
       → 同步 theme 类 + 侧栏（必要时点切换按钮）
       → stabilize（禁动画 / 藏图 / shell 场景遮罩主内容）
       → screenshot
  → 对比 baseline
```

**旧逻辑问题：** 只 `networkidle` + 固定 1s sleep，内容半加载就切下一页——你看到的「一直在切」。
**现逻辑：** 壳就绪 + 网络安静 + 布局稳定后再截；shell 场景仍遮罩主内容（验导航壳，不验 feed 像素）。

主进程配合：`squirrel-desktop/src/main.mjs`

- `SQUIRREL_VISUAL_TEST=1` → 独立 `userData`，不抢已运行实例的 single-instance lock
- 日常用户启动行为不变

---

## 命令

在 `squirrel-desktop/`：

| 命令 | 作用 |
|------|------|
| `npm run visual:snapshot` | 截图到 `runtime-logs/visual-actual/` |
| `npm run visual:update` | actual → `renderer/visual-baselines/`（**本地**，PNG 不提交） |
| `npm run visual:check` | 与本地 baseline 像素对比 |

### 前置

1. **Vite renderer 已起**（`npm run dev:renderer` 或完整 `npm run dev`）
2. **后端可登录**（脚本读仓库根 `.env.dev` 的 `DEV_AUTH_EMAIL` / `DEV_AUTH_PASSWORD`）
3. 不必手开 Electron；脚本会自己 launch 测试实例

### 环境变量

| 变量 | 说明 |
|------|------|
| `VISUAL_DRIVER` | `electron`（默认）\| `browser`（仅布局探针） |
| `VISUAL_BASE_URL` | Vite 地址；默认自动探测 5173–5176 的 squirrel 壳 |
| `DESKTOP_RENDERER_URL` | 传给 Electron 的 renderer URL（默认 = BASE_URL） |
| `DEV_AUTH_*` / `VISUAL_*` | 登录；优先环境变量，否则 `.env.dev` |
| `VISUAL_TOKEN` | JWT，跳过表单登录 |
| `SQUIRREL_VISUAL_USER_DATA` | Electron userData 目录（默认系统临时目录） |
| `VISUAL_ELECTRON_PATH` | 可选，覆盖 electron 二进制 |
| `VISUAL_THRESHOLD` / `VISUAL_MAX_DIFF_PIXELS` | 像素容忍 |
| `VISUAL_OUT_DIR` / `VISUAL_BASELINE_DIR` | 输出与基线路径 |

### 场景

| id | 意图 |
|----|------|
| `shell-home-dark` / collapsed / light | 桌面壳（侧栏+标题栏区域）；主内容遮罩防 feed 抖动 |
| `videos-dark` / `rss-dark` / `music-dark` / `settings-dark` | 主页面布局（媒体图隐藏以稳定像素） |

---

## 工作流

### 布局 / 壳变更

1. 对照 [ui-clone-anchors.md](./ui-clone-anchors.md)
2. 改代码
3. `npm run visual:update`（**Electron 默认**；PNG **不提交 git**）
4. 本机目检 PNG
5. `npm run visual:check` 本机通过

### 桌面功能（IPC）变更

- 截图契约仍用 Electron 驱动
- 功能正确性另用主进程单测 / 手工；视觉脚本至少保证 `desktopApp` 桥存在且页面可进

### 禁止

- 用 **browser** 驱动更新正式 baseline 却声称「桌面已验」
- 无锚点依据的截图审美循环
- 把账密写进脚本或提交进库

---

## 与 Agents / 评审

| 规则 | 说明 |
|------|------|
| 默认验收载体 | **Electron + CDP**，不是独立浏览器 |
| UI 分析 | 代码 + 锚点文档为主 |
| 布局合入 | 本机 `visual:check`（electron）通过；baseline PNG 仅本地，不进仓库 |
| browser 驱动 | 仅调试布局，不作为桌面发布门槛 |

阻断项见 [governance.md](./governance.md)。
