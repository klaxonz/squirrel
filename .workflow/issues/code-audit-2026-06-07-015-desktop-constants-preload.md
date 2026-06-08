---
title: 'Desktop: 硬编码常量散落 + 重复 preload + 空 feed 目录'
status: fixed
fixed_by: constants.mjs, media-headers.mjs, window.mjs (+11 files)
severity: medium
category: code-smell
location: 全局 — constants.mjs:57, playback/file-cache.mjs:20, playback/providers/shared/adult-page.mjs:3, preload.cjs/preload.mjs, src/feed/
---

## 问题描述

1. **硬编码 Chrome 版本**：多个模块硬编码 `Chrome/123`、`Chrome/124`、`Chrome/135`，而 `constants.mjs` 定义有 `desktopChromeUserAgent` 动态生成。

2. **缓存 TTL 不统一**：`playback/file-cache.mjs:20` 和 `adult-page.mjs:3` 都硬编码 `5 * 60 * 1000`，未引用常量。

3. **重复 preload 文件**：`preload.cjs` 和 `preload.mjs` 暴露相同 API，但 `window.mjs:262` 使用 `.cjs` 版本。ESM 项目中出现 CJS preload 令人困惑。

4. **空 src/feed/ 目录**：目录存在但空无一物，疑似未完成功能。

5. **静默吞异常**：多处 `catch {}` 空块不记录任何日志。

## 建议方向

1. User-Agent 统一到 `constants.mjs`，各模块 import 使用
2. 定义 `CACHE_TTL_MS` 常量在 `constants.mjs`
3. 选择并保留一个 preload 文件，移除另一个
4. 移除空 feed/ 目录或添加 .gitkeep + 说明
5. 空 catch 块至少添加 `console.debug` 日志
