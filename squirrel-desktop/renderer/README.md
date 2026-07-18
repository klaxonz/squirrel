# Squirrel Desktop · Renderer

Vue 3 + Vite UI。桌面端只维护这一套前端（Electron 加载本包）。

| | |
|--|--|
| 开发 | 仓库根 `npm run dev:desktop`，或 `squirrel-desktop` 内 `npm run dev` |
| 构建 | `npm run build:renderer` → `renderer/dist` |
| 类型检查 | `npm run typecheck` |
| 单测 | `npm run test:renderer`（仅测真实逻辑，见 `vitest.config.ts`） |
| 设计方向 | [docs/design/direction.md](./docs/design/direction.md) |
| 包说明 | [../README.md](../README.md) |

实现真源：`src/shared/styles/**`、`src/shared/ui/**`、`src/app/**`、`src/features/**`。
