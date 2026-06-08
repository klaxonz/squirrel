---
title: 代码审查汇总 2026-06-08（第三轮）
scope: 全量 — backend / sdk / desktop / frontend / extension / site-runtimes / cf-bypass / music-api
---

## 总览

| 严重度 | 新增 | 前轮仍 Open | 合计 |
|--------|------|-------------|------|
| Critical | 1 | 0（前轮 5 已 fixed） | 1 |
| High | 2 | 4（#023/#033/#014/#016） | 6 |
| Medium | 6 | 2（#035/#040） | 8 |
| Low | 3 | 0 | 3 |
| **Total** | **12** | **6** | **18** |

> 前轮 39 个 issue 中 32 个已标记 fixed，6 个仍 open（#001/#002/#003/#014/#016/#023/#033/#035/#040）。

## 本轮新增问题（优先级排序）

| # | 严重度 | 类别 | 问题 | 子项目 | 参考 |
|---|--------|------|------|--------|------|
| 1 | **critical** | security | JWT 随机默认值导致重启后所有会话失效 | backend | #044 |
| 2 | **high** | error-handling | CF-bypass 8 处静默吞异常无日志 | cf-bypass | #045 |
| 3 | **high** | code-smell | YouPorn 缓存键用二进制标志而非 SHA1 哈希 | desktop | #046 |
| 4 | **medium** | error-handling | 进度同步失败时重试队列无限增长 | frontend | #047 |
| 5 | **medium** | security | shell.openExternal 未校验协议 | desktop | #048 |
| 6 | **medium** | architecture | VideoService/SubscriptionService 空壳门面类 | backend | #049 |
| 7 | **medium** | performance | YouTubei session 缓存无界增长 | desktop | #050 |
| 8 | **medium** | architecture | 中间件顺序导致 AccessLog 缺 trace_id | backend | #051 |
| 9 | **medium** | security | Auth 中间件 startswith 路径匹配可绕过 | backend | #052 |
| 10 | **low** | resource-leak | webRequest 监听器从未移除 | desktop | #053 |
| 11 | **low** | dead-code | BackendPlayerAdapter 未用字段 + 空 catch-rethrow | frontend | #054 |
| 12 | **low** | error-handling | usePlayer.ts 空 catch 丢弃 localStorage 错误 | frontend | #055 |

## 优先级最高的 5 个问题

| # | 严重度 | 类别 | 问题 | 参考 |
|---|--------|------|------|------|
| 1 | **critical** | security | JWT 随机默认值导致重启会话失效 | #044 |
| 2 | **high** | error-handling | CF-bypass 8 处静默吞异常 | #045 |
| 3 | **high** | code-smell | YouPorn 缓存键 bug 导致缓存污染 | #046 |
| 4 | **medium** | architecture | 中间件顺序导致 trace 缺失 | #051 |
| 5 | **medium** | security | Auth startswith 路径匹配绕过 | #052 |

## 仍然 Open 的前轮问题

| # | 严重度 | 类别 | 问题 | 参考文件 |
|---|--------|------|------|----------|
| 001 | critical | security | CF-bypass SSRF 无认证 | code-audit-2026-06-07-001 |
| 002 | high | security | Frontend XSS 通过 RSS v-html | code-audit-2026-06-07-002 |
| 003 | critical | security | Desktop webSecurity: false 禁用同源策略 | code-audit-2026-06-07-003 |
| 014 | high | security | Extension 安全问题 | code-audit-2026-06-07-014 |
| 016 | medium | test | SDK 全局状态测试覆盖不足 | code-audit-2026-06-07-016 |
| 023 | high | security | Extension webSecurity 问题 | code-audit-2026-06-07-023 |
| 033 | high | test | 前端无测试 + Desktop 测试脆弱 | code-audit-2026-06-07-033 |
| 035 | medium | api-design | REST 不一致 | code-audit-2026-06-07-035 |
| 040 | medium | architecture | Backend services/ 57 文件无命名空间 | code-audit-2026-06-07-040 |

## 改进建议

### 1. JWT 重启会话失效（#044）
**思路：** 启动时校验环境变量，缺失则报错退出；或首次写入 data/jwt_secret.key 持久化
**参考：** `.opencode/issues/code-audit-2026-06-08-044-jwt-secret-regenerated-on-restart.md`

### 2. CF-bypass 异常吞噬（#045）
**思路：** 8 个 except 块加 `logger.warning(exc_info=True)`，保留不崩溃行为同时提供可观测性
**参考：** `.opencode/issues/code-audit-2026-06-08-045-cf-bypass-browser-solver-silent-excepts.md`

### 3. YouPorn 缓存键 bug（#046）
**思路：** 对齐其他 provider 的 SHA1 cookie 哈希，抽取共享工具函数到 playback-cache.mjs
**参考：** `.opencode/issues/code-audit-2026-06-08-046-youporn-cookie-cache-key-bug.md`

### 4. 中间件顺序（#051）
**思路：** RequestContextMiddleware 作为最外层注册，确保 trace_id 贯穿全请求生命周期
**参考：** `.opencode/issues/code-audit-2026-06-08-051-backend-middleware-ordering-trace-id.md`

### 5. Auth 路径匹配（#052）
**思路：** 静态路径精确匹配 + 路径分隔符防护，参数化路径用 regex 替代 startswith
**参考：** `.opencode/issues/code-audit-2026-06-08-052-backend-auth-path-bypass-startswith.md`

## 审查方发现

### 合规检查（AGENTS.md）

| 规则 | 结果 |
|------|------|
| 修改 site_runtimes/ 下 .py | ✅ 无违规 |
| 修改 .env / 凭据 | ✅ `.env.dev` / `.env.test` 未追踪 |
| 桌面播放不上后端兜底 | ✅ 无后端 `/api/video/url` 引用 |
| ESM 模块 | ✅ `package.json` 均有 `"type": "module"` |
| 前端不维护区域 | ✅ 未触及 |
| 未提交改动 | ✅ 工作区干净 |

### 积极发现

- ♻️ 前轮 32/39 个 issue 已修复，说明团队在持续改进
- 🧪 113 个 pytest 测试文件，覆盖较好
- 🔒 无硬编码生产凭据、无 `shell=True`、无 `eval()`
- 🏗️ desktop 播放架构清晰：provider 模式 + 缓存层 + 独立 preload
