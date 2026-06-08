---
title: CF-bypass browser_solver.py 8 处静默吞异常
status: fixed
severity: high
category: error-handling
location: squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py:237,246,273,294,360,397,430,440
fixed_by: squirrel-cf-bypass/src/squirrel_cf_bypass/app/core/browser_solver.py:237,247,274,295,361,398,431,441
---

## 问题描述

Cloudflare 绕过核心组件 `browser_solver.py` 包含 8 个 `except Exception:` 块，要么静默返回 `None`，要么静默 `continue`，没有任何日志记录。这是生产环境中关键的故障排除组件——任何被吞没的异常都可能掩盖真正的绕过失败。

具体位置：
- **L237-238**: `except Exception: continue` — Turnstile 检测循环内
- **L246-247**: `except Exception: return None` — Interstitial 检测失败
- **L273-274**: `except Exception: return None` — 页面 evaluate() 失败
- **L294-295**: `except Exception: continue` — 验证码轮询重试
- **L360-361**: `logger.warning(...)` — 有日志但返回 None
- **L397-398**: `logger.warning(...)` — 导航失败
- **L430-431**: `logger.warning(...)` — 验证码求解失败
- **L440-441**: `except Exception: return None` — 上下文清理失败

## 影响

- 绕过失败时无任何线索，运维无法诊断
- 问题积累到用户报告才发现
- 难以区分是 Cloudflare 规则变更还是代码 bug

## 建议方向

在每个 `except` 块中调用 `logger.warning("context message", exc_info=True)` 或 `logger.exception()`，记录异常时的选择器、URL、重试次数等上下文。
