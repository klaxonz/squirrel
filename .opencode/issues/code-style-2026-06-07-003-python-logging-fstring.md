---
title: 'Python: 多处 logging 使用 f-string 而非 %s 延迟格式化'
status: open
severity: low
category: code-smell
created: 2026-06-07
location: squirrel-backend/, squirrel-site-runtimes/
---

## 问题描述

AGENTS.md 约定 logging 使用 `%s` 延迟格式化（避免在日志级别未启用时执行字符串格式化），但仍有反例：

### backend
- `squirrel-backend/routes/sites.py` 等文件：
  ```python
  logger.error(f"get_site_from_url exception occurred: url={url}, error={e!s}", exc_info=True)
  ```

### site-runtimes
- `bilibili/extractor.py` 等：
  ```python
  logger.error(f"YouTube视频信息提取失败: {url}", exc_info=True)
  ```

## 影响

- 当日志级别为 WARNING 或更高时，f-string 仍会被求值（微小性能损失）
- 违反项目约定，代码审查时产生噪音
- `ruff` 的 `G` 规则（flake8-logging）可检测此类问题

## 建议方向

1. 全局搜索 `logger\.(info|debug|warning|error|exception)\(f"` 模式
2. 替换为 `logger.error("... %s", url, exc_info=True)` 风格
3. 在 ruff 配置中启用 `flake8-logging`（G）规则防止回潮
