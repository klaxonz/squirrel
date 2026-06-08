---
title: 代码审查汇总 2026-06-07（第二轮）
scope: 全量扫描 — backend / sdk / desktop / frontend / site-runtimes / cf-bypass / music-api
---

## 总览

| 严重度 | 轮次1 | 轮次2（本轮新增） | 总计 |
|--------|-------|-------------------|------|
| Critical | 6 | — | 6（轮次1未修复） |
| High | 13 | 6 | 19 |
| Medium | 4 | 4 | 8 |
| Low | — | 1 | 1 |
| **Total** | **23** | **16** | **39** |

## 本轮新增问题

| # | 严重度 | 类别 | 问题 | 子项目 |
|---|--------|------|------|--------|
| 029 | high | error-handling | Desktop 零可观测性 — 全部 `catch {}` 无日志 | desktop |
| 030 | high | error-handling | Frontend 50+ 处静默吞异常 | frontend |
| 031 | high | performance | 5 处 N+1 查询 + 2 处无界内存 + 冗余 deepcopy | backend |
| 032 | high | concurrency | 无锁全局 HTTP 客户端 + 配置缓存 + 调度器作业 | backend |
| 033 | high | test-quality | 前端零测试 + Desktop 源码正则脆弱测试 | frontend/desktop |
| 034 | high | dead-code | 1700+ 行孤立模块 + 未使用模型 + 幽灵依赖 | backend/全量 |
| 035 | medium | api-design | 动词 URL / 无版本 / 响应格式不统一 | backend |
| 036 | medium | test-quality | 后端过度 Mock（1190 处 patch） | backend |
| 037 | low | naming | `result`/`data`/`info` 泛滥 + 风格不一致 | 全量 |
| 038 | medium | error-handling | trace_id 未覆盖调度/队列/SDK/Frontend | 全量 |
| 039 | high | architecture | Backend 分层倒置：core→services、utils→services、routes→routes | backend |
| 040 | medium | architecture | Backend services/ 57 个顶层文件 + 缺少 src/ 布局 | backend |
| 041 | medium | architecture | Frontend axios→composables 反向依赖 + 3 处 remote-channel 重复 | frontend |
| 042 | medium | architecture | Desktop IPC 单体 321 行 + main.mjs 耦合 YouTube | desktop |
| 043 | low | dead-code | 多处废弃子包 + 空目录 + 搁置抽象 | backend/frontend |

## 优先级最高的 5 个问题

| # | 严重度 | 类别 | 问题 | 参考 |
|---|--------|------|------|------|
| 1 | **high** | error-handling | Desktop 全部错误静默吞噬无日志 | #029 |
| 2 | **high** | concurrency | 无锁 HTTP 客户端多线程竞争导致崩溃 | #032 |
| 3 | **high** | error-handling | Frontend 50+ 静默 catch 操作无声失败 | #030 |
| 4 | **high** | architecture | Backend 分层倒置：core→services 依赖向后 | #039 |
| 5 | **high** | performance | N+1 查询 + 无界内存 OOM 风险 | #031 |

## 改进建议

### 1. Desktop 零可观测性（#029）
**修复思路：** 引入 `electron-log`，所有 `catch {}` 改为 `catch (err) { logger.error(…) }`，关键路径加 console.warn 分级输出
**参考：** `.opencode/issues/code-audit-2026-06-07-029-desktop-zero-observability.md`

### 2. 全局无锁 HTTP 客户端竞争（#032）
**修复思路：** `thumbnail_refresh_task.py` 添加 threading.Lock 保护 client 重建，或使用 ThreadLocal 模式；user_config_service 加锁
**参考：** `.opencode/issues/code-audit-2026-06-07-032-concurrency-global-mutable-state.md`

### 3. Frontend 静默异常吞噬（#030）
**修复思路：** 利用已有 Logger 在 catch 中至少日志，用户操作场景加 toast 反馈
**参考：** `.opencode/issues/code-audit-2026-06-07-030-frontend-silent-error-swallowing.md`

### 4. N+1 查询 + 内存问题（#031）
**修复思路：** 批量查询替代循环查询、流式读取日志、deepcopy 改为拷贝/缓存
**参考：** `.opencode/issues/code-audit-2026-06-07-031-performance-n-plus-one-and-memory.md`

### 5. 孤立模块 + 幽灵依赖（#034）
**修复思路：** 逐模块确认去留（确认后删除或标废弃），清理 Pipfile/package.json 未使用依赖
**参考：** `.opencode/issues/code-audit-2026-06-07-034-dead-code-orphan-modules.md`

### 6. Backend 分层倒置：core→services（#039）
**修复思路：** `core/extraction/services/` 依赖注入反转，或 extraction 提升为顶层包；jwt_helper 改为接口注入
**参考：** `.opencode/issues/code-audit-2026-06-07-039-architecture-layered-inversion-core-services.md`

### 7. Backend services/ 57 个文件无命名空间（#040）
**修复思路：** 按领域分组（subscription/, video/），迁移至 src/ 布局，清理 __init__.py
**参考：** `.opencode/issues/code-audit-2026-06-07-040-architecture-services-overcrowded-and-no-src-layout.md`
