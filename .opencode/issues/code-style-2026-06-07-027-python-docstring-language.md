---
title: 'Python: 子项目间 docstring 语言不统一（中文 vs 英文）'
status: fixed
fixed_by: AGENTS.md:62
severity: low
category: code-smell
created: 2026-06-07
location: squirrel-backend/, squirrel-sdk/, squirrel-site-runtimes/
---

## 问题描述

Python 子项目之间 docstring 语言不统一：

- **backend**：中文 docstring
  ```python
  """构建基础视频查询，以 Video 为主表。"""
  ```
- **SDK**：英文 docstring（Google-style）
  ```python
  """Protocol for extractor plugins."""
  ```
- **site-runtimes**：混合 — Bilibili 用中文，YouPorn/YouTube 用英文

已有 issue #022 提及 SDK `http.py` 中英文混用，但整体语言策略未定义。

## 影响

- 跨子项目阅读时切换语言
- 新贡献者不确定使用哪种语言
- 无自动化手段检测

## 修复

约定改为全部英文（Google-style），并批量替换了所有现有中文 docstring。

## 改动量

82 个文件中的 379 个中文 docstring 全部替换为英文。
