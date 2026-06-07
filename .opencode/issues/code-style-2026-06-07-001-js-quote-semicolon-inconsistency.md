---
title: 'JS/TS: 子项目间引号和分号风格不统一'
status: open
severity: low
category: code-smell
created: 2026-06-07
location: squirrel-frontend/, squirrel-desktop/, squirrel-extension/, squirrel-music-api/
---

## 问题描述

JS/TS 子项目之间引号和分号风格不一致，增加上下文切换成本：

### 引号
- **frontend**（TS）：单引号 `'`
- **desktop**（.mjs）：单引号 `'`
- **extension**（.js）：双引号 `"`
- **music-api**（CJS）：单引号 `'`

### 分号
- **frontend/desktop**：省略（ASI 风格）
- **extension**：全部保留

### 异步风格
- **extension background.js**：使用 `.then()` 链式调用
- **其余所有文件**：使用 `async/await`

## 影响

- 跨子项目阅读和维护时需要切换心智模型
- 无法统一配置 linter/formatter
- `extension` 同时混用两种异步风格（popup.js/options.js 用 async/await，background.js 用 .then()），内部也不一致

## 建议方向

1. 统一 extension 为单引号 + 无分号（与其他子项目一致）
2. 统一 extension 异步风格为 `async/await`
3. 或扩展为全项目统一的 ESLint 配置
