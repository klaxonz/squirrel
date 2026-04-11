# Squirrel Desktop

`squirrel-desktop` 是一个 Electron 桌面端子项目，复用现有 Squirrel Web UI，不再维护第二套前端页面。

## 设计

- 开发模式：启动 `squirrel-frontend` 的 Vite dev server，再由 Electron 加载该地址。
- 打包运行：Electron 默认加载 `http://127.0.0.1:8001`，也可以通过环境变量指向其他 Squirrel Web 地址。
- preload 会注入 `window.desktopApp`，前端可显式识别桌面端能力。

## 命令

```bash
npm install
npm run dev
npm run build
npm run dist
```

- `npm run dev`：开发模式，要求后端已启动在 `http://127.0.0.1:8001`，或通过 `VITE_BACKEND_URL` 覆盖。
- `npm run build`：生成 unpacked 桌面端产物。
- `npm run dist`：生成安装包。

## 环境变量

- `DESKTOP_APP_URL`：桌面端正式运行时加载的页面地址，默认 `http://127.0.0.1:8001`
- `DESKTOP_RENDERER_URL`：仅开发模式使用，默认 `http://127.0.0.1:5173`
- `VITE_BACKEND_URL`：开发模式下前端代理目标，默认 `http://127.0.0.1:8001`
