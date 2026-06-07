---
title: 'SDK: "stdlib-only" 承诺不实 + beautifulsoup4 未声明依赖'
status: open
severity: high
category: architecture
location: squirrel-sdk/README.md:107, src/crawl/core.py:3-5, src/crawl/importer.py:8, pyproject.toml:17-19
---

## 问题描述

1. **虚假承诺**：README 和 `core.py` 声称 SDK "standard library only"、"distribution-free"，但 `pyproject.toml` 声明了 `requests>=2.31.0` 硬依赖，且 `__init__.py` 无条件 import `http.py`（imports requests）。

2. **缺失依赖**：`src/crawl/importer.py:8` 导入 `from bs4 import BeautifulSoup` 并广泛使用，但 `beautifulsoup4` 未在任何地方声明（`pyproject.toml`、`Pipfile`、`requires.txt`）。

## 影响

- 任何使用 SDK 的代码都会拉取 requests，与 "stdlib-only" 承诺矛盾
- 使用 BaseImporter/PaginatedImporter 的消费者会因 ImportError 崩溃
- 误导评估 SDK 体积的开发者

## 建议方向

1. 两种方案二选一：(a) 移除 stdlib-only 声明，透明地列出依赖；(b) 将 HTTP/importer 模块通过延迟 import 变为可选
2. 将 `beautifulsoup4>=4.12` 添加到 `pyproject.toml` 和 `Pipfile`
