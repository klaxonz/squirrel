---
title: 测试 — 前端零测试 + Desktop 源码正则脆弱测试
status: open
severity: high
category: test-quality
location: squirrel-frontend/tests/（不存在）, squirrel-desktop/tests/site-login.test.mjs, youtube-provider.test.mjs
---

## 问题描述

### 前端零测试
`squirrel-frontend/` 没有任何测试文件。虽然前端有 35+ Vue 组件、25+ composables、10+ API 封装、5+ stores，但全部零覆盖。

未被测试覆盖的关键路径：
- 视频播放器（VideoPlayer 2673 行 + 插件系统 3000+ 行）
- 全部 composables（usePlaybackOrchestrator、useRssFeeds 等）
- API 调用层（request.ts、各 api/*.ts）
- Pinia stores（user、musicPlayer 等）
- 路由守卫和导航

### Desktop 源码正则脆弱测试
**`squirrel-desktop/tests/site-login.test.mjs`** 和 **`youtube-provider.test.mjs`** 共 31 个断言均通过 `readFile` 读取源码后用 `assert.match` 正则匹配代码文本。这些测试测试的是"代码说什么"而非"代码做什么"——任何格式化/重构都会破坏它们。

### SDK 测试覆盖不足（已有 issue 016）
已有 `#016` 但问题仍未改善——SDK 仍只有 1 个测试文件。

## 影响

- 前端重构无安全网，改播放器或 composables 极易引入回归
- Desktop 源码正则测试实际上阻止了重构（格式化即挂）
- SDK 无测试掩盖了隐式依赖问题

## 建议方向

1. 前端引入 Vitest + Vue Test Utils，至少覆盖 composables 和 stores
2. Desktop 源码正则测试改为 mock-based 行为测试
3. SDK 按协议接口补集成测试，覆盖 extractor + importer 核心路径
