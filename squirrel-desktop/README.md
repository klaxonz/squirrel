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
