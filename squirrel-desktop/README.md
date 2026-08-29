# Squirrel Desktop

Electron 桌面端：主进程（登录 / 搜索 / 播流）+ 内嵌 Vue renderer。只维护这一套 UI。

## 布局

```
squirrel-desktop/
  src/           # Electron main / preload / IPC
  renderer/      # Vue 3 + Vite UI（原 squirrel-frontend）
  scripts/       # dev / native rebuild
```

## 命令

```bash
# 仓库根目录
npm install
npm run dev:desktop

# 或在本包内
cd squirrel-desktop
npm run dev              # Vite renderer + Electron
npm run build:renderer   # 仅构建 UI → renderer/dist
npm run build            # UI + electron-builder --dir
npm run dist             # UI + 安装包
npm run typecheck
npm run test             # main-process tests
npm run test:renderer    # Vue/vitest
```

## 加载方式

| 模式 | Renderer |
|------|----------|
| `npm run dev` | Vite `http://127.0.0.1:5174`（`DESKTOP_RENDERER_URL`） |
| 打包 / 本地 dist | `renderer/dist/index.html`（`file://` via `loadFile`） |

后端 API 默认 `http://127.0.0.1:8001`，开发时代理见 `renderer/vite.config.ts`。

## 环境变量

- `DESKTOP_RENDERER_URL`：开发模式 renderer 地址，默认 `http://127.0.0.1:5174`
- `VITE_BACKEND_URL`：开发时 Vite 代理目标后端，默认 `http://127.0.0.1:8001`（仅 dev；运行时 API 地址由桌面端 server-config 配置）

打包后 renderer 使用 hash 路由（`createWebHashHistory`），以便在 `file://` 下正常导航。

preload 注入 `window.desktopApp`（`isDesktop: true` 及站点登录 / 播流 / 窗口控制等）。

## Electron 自动化测试

`npm run test:electron` 使用 Electron 官方 automated testing 推荐的 WebdriverIO Electron service（`@wdio/electron-service`）启动真实未打包应用。测试加载本地 fixture，不访问外网，并通过独立临时 `userData` 目录验证 `BrowserWindow` 和 preload `contextBridge` 注入。

依赖安装后若需要跳过 native rebuild，可先执行 `npm install --ignore-scripts`，再运行 `npm run test:electron`。

## AI-only visual review harness

The harness is deterministic and offline by default; it never calls a real site or uses credentials. It writes `candidate/`, `baseline/`, `diff.json`, `manifest.json`, DOM/style/task evidence, `automation-verdict.json`, and separate JSON inputs for visual AI and task AI. AI review is an input-generation step, not an automated claim of approval.

```bash
npm run visual:review                         # deterministic fixture; baseline is never changed
npm run visual:review:update-baseline         # explicit baseline update only
VISUAL_REVIEW_OUT=visual-review-results npm run test:electron -- --spec tests/electron-smoke/visual-review.spec.mjs
```

`visual:review` validates the fixed manifest (scenario, viewport, Electron/OS, locale, theme, fixture, prompt version), checks contrast, raw styles, overflow, accessible names, console errors, and task evidence. The Electron collector uses the existing WebdriverIO Electron service and captures only renderer content; OS-native windows/dialogs are excluded from pixel baselines. If chromedriver/Electron cannot start, the deterministic fixture remains available and the Electron result must be reported as blocked, never as a passed business screenshot.

The daily checks (`npm run check`) enforce existing typography/overlay rules plus the offline harness. `test:electron` is a real Electron runtime smoke boundary; `visual:review` is deterministic evidence generation; computer-use/manual review is outside npm automation and must consume the generated prompts/artifacts.

重要：默认 `visual:review` 的 deterministic fixture 仅是 smoke-only，业务视觉 verdict 固定为 `blocked` 并以非零退出；它不能代表 renderer-app 或业务页面通过。只有 `visual-review.spec.mjs` 在真实 Electron renderer 成功采集、且 manifest provenance 为 `mode: electron` / `target: business` 时，才可对业务证据运行通过/失败门禁。当前仓库未声称已覆盖真实业务视觉 baseline；缺少 baseline、runtime 或 AI review 均保持 blocked。
