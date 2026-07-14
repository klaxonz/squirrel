# Visual baselines

PNG baselines for `npm run visual:check`（见 [docs/design/visual-verification.md](../docs/design/visual-verification.md)）。

## 不入库

`*.png` **不要提交**（已在仓库根 `.gitignore`）。每人 / 每台机器本地生成：

```bash
# squirrel-desktop/，先起 Vite renderer + 后端
npm run visual:update   # 写入本目录 *.png
npm run visual:check    # 与本地 baseline 对比
```

- 账密：仓库根 `.env.dev` 的 `DEV_AUTH_*`（也不提交）
- 驱动：默认 Electron + CDP
- 无锚点依据不要为了「变绿」盲更 baseline

本目录仅保留本 README 进版本库。
