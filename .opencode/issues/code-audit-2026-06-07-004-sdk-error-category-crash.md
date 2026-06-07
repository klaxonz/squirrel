---
title: 'SDK: ErrorCategory.INTERNAL 不存在导致运行时崩溃'
status: fixed
fixed_by: squirrel-sdk/src/crawl/extractor.py:85
severity: critical
category: code-smell
location: squirrel-sdk/src/crawl/extractor.py:85
---

## 问题描述

`extractor.py:85` 引用 `ErrorCategory.INTERNAL`，但 `ErrorCategory` 枚举中只有 NETWORK、RATE_LIMIT、AUTH、VIP、NOT_FOUND、PARSE、UNKNOWN，没有 INTERNAL。`except Exception` 捕获块内的处理逻辑本身就会抛 AttributeError。

## 影响

视频提取过程中任何非 PluginError 的非预期异常都会导致 AttributeError 崩溃，而非优雅失败。这破坏了异常统一处理体系。

## 建议方向

将 `ErrorCategory.INTERNAL` 改为 `ErrorCategory.UNKNOWN`（line 85）。
