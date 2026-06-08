---
title: 代码审查汇总 2026-06-09（第四轮）
scope: 全量 — backend / sdk / desktop / frontend / extension / site-runtimes / cf-bypass / music-api
---

## 总览

| 严重度 | 本轮新增 | 前轮仍 Open | 合计 |
|--------|----------|-------------|------|
| Critical | 1 | 4（#001/#002/#003/#056）| 5 |
| High | 4 | 4（#014/#023/#033/#046）| 8 |
| Medium | 4 | 7（#016/#035/#040/#047/#049/#050/#051/#052）| 11 |
| Low | 1 | 3（#053/#054/#055）| 4 |
| **Total** | **10** | **18** | **28** |

> 前轮 55 个 issue 中 37 个已 fixed，18 个仍 open。

## 本轮新增问题（优先级排序）

| # | 严重度 | 类别 | 问题 | 子项目 | 参考 |
|---|--------|------|------|--------|------|
| 1 | **critical** | security | Path Traversal — Log/Cookie/Icon 任意文件读取 | backend | #056 |
| 2 | **high** | architecture | CF-Bypass 浏览器上下文内存泄漏 + Lock 无界增长 | cf-bypass | #060 |
| 3 | **high** | security | CF-Bypass x-proxy 头注入 MITM（补充 #001） | cf-bypass | #061 |
| 4 | **high** | security | Extension XSS innerHTML + URL 匹配绕过 + 登录无状态检查 | extension | #062 |
| 5 | **high** | security | KuGou 硬编码 WeChat 密钥和签名密钥 | music-api | #063 |
| 6 | **medium** | security | SQL ILIKE 通配符注入 7 处 | backend | #057 |
| 7 | **medium** | architecture | httpx AsyncClient 资源泄漏（MusicClient + Thumbnail） | backend | #058 |
| 8 | **medium** | security | 默认数据库密码 postgres | backend | #059 |
| 9 | **medium** | architecture | Bilibili WBI 缓存竞态 + SDK 无连接复用 | site-runtimes/sdk | #064 |
| 10 | **low** | security | Runtime Bridge 动态 import 注入风险 | backend | #065 |

## 优先级最高的 5 个问题

| # | 严重度 | 问题 | 修复思路 | 参考 |
|---|--------|------|----------|------|
| 1 | **critical** | 路径遍历任意文件读取 | `Path.resolve()` + `is_relative_to()` 校验 | #056 |
| 2 | **high** | CF-Bypass 内存泄漏 OOM | 为 `_browser_entries` 加上限和 TTL 淘汰 | #060 |
| 3 | **high** | x-proxy 头 MITM + SSRF | 认证中间件 + 代理白名单 + 内网 IP 拒绝 | #061 |
| 4 | **high** | Extension XSS + 登录绕过 | `textContent` 替换 `innerHTML` + URL 精确匹配 | #062 |
| 5 | **high** | KuGou 硬编码密钥 | 迁移至环境变量，排除 node_modules 敏感文件 | #063 |

## 仍然 Open 的前轮问题

| # | 严重度 | 类别 | 问题 | 参考文件 |
|---|--------|------|------|----------|
| 001 | critical | security | CF-bypass SSRF 无认证 | code-audit-2026-06-07-001 |
| 002 | high | security | Frontend XSS 通过 RSS v-html | code-audit-2026-06-07-002 |
| 003 | critical | security | Desktop webSecurity: false | code-audit-2026-06-07-003 |
| 014 | high | security | Extension 安全问题 | code-audit-2026-06-07-014 |
| 016 | medium | test | SDK 全局状态测试覆盖不足 | code-audit-2026-06-07-016 |
| 023 | high | security | Extension webSecurity 问题 | code-audit-2026-06-07-023 |
| 033 | high | test | 前端无测试 + Desktop 测试脆弱 | code-audit-2026-06-07-033 |
| 035 | medium | api-design | REST 不一致 | code-audit-2026-06-07-035 |
| 040 | medium | architecture | Backend services/ 57 文件无命名空间 | code-audit-2026-06-07-040 |
| 045 | high | error-handling | CF-bypass 8 处静默吞异常 | code-audit-2026-06-08-045 |
| 046 | high | code-smell | YouPorn 缓存键 bug | code-audit-2026-06-08-046 |
| 047 | medium | error-handling | 进度同步重试队列无限增长 | code-audit-2026-06-08-047 |
| 048 | medium | security | shell.openExternal 未校验协议 | code-audit-2026-06-08-048 |
| 049 | medium | architecture | VideoService/SubscriptionService 空壳门面 | code-audit-2026-06-08-049 |
| 050 | medium | performance | YouTubei SESSION_CACHE 无界增长 | code-audit-2026-06-08-050 |
| 051 | medium | architecture | 中间件顺序缺 trace_id | code-audit-2026-06-08-051 |
| 052 | medium | security | Auth startswith 路径匹配绕过 | code-audit-2026-06-08-052 |
| 053 | low | resource-leak | webRequest 监听器未移除 | code-audit-2026-06-08-053 |
| 054 | low | dead-code | BackendPlayerAdapter 未用字段 | code-audit-2026-06-08-054 |
| 055 | low | error-handling | usePlayer.ts 空 catch | code-audit-2026-06-08-055 |

## 合规检查（AGENTS.md）

| 规则 | 结果 |
|------|------|
| 修改 site_runtimes/ 下 .py | ✅ 无违规（只读审查） |
| 修改 .env / 凭据 | ✅ 未修改 |
| 桌面播放不上后端兜底 | ✅ 无后端 `/api/video/url` 调用 |
| ESM 模块 | ✅ 所有 package.json 有 `"type": "module"` |
| 未提交改动 | ✅ 只读模式，无代码变更 |

## 积极发现

- 📊 四轮审查累计 65 个 issue，37 个已修复（57% 修复率）
- 🔒 无硬编码生产凭据（backend 核心代码）、无 `shell=True`、无 `eval()`
- 🧪 后端测试覆盖 113 个 pytest 文件
- 🏗️ Desktop 播放架构保持清晰：provider 模式 + 缓存层 + 独立 preload
- ✅ SDK 异常类层次设计良好，站点插件正确在边界翻译错误类型