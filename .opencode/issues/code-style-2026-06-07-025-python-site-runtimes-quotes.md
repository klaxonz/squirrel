---
title: 'Python: site-runtimes 子项目间引号风格不统一'
status: fixed
fixed_by: squirrel-sdk/pyproject.toml, squirrel-cf-bypass/pyproject.toml, squirrel-site-runtimes/*/pyproject.toml
severity: low
category: code-smell
created: 2026-06-07
location: squirrel-site-runtimes/*/src/
---

## 问题描述

site-runtimes 各插件之间引号风格混用：

- **Bilibili 插件**：双引号 `"`
- **YouTube 插件**：单引号 `'`
- **YouPorn/JavDB 插件**：单引号 `'`

已有 issue #022 记录了 backend 的双引号问题，但 site-runtimes 的混用尚未覆盖。

## 影响

- 同一子项目内风格分裂
- 无法统一配置 ruff 引号规则
- 新插件开发时无明确风格指引

## 建议方向

1. 统一 site-runtimes 为单引号（与 SDK 一致）
2. 运行 `ruff check --fix --select Q` 批量修复
3. 在 AGENTS.md 或 pyproject.toml 中明确约定
