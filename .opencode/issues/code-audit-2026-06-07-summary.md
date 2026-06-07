---
title: 代码审查汇总 2026-06-07
scope: 全量扫描 — backend / sdk / desktop / frontend / site-runtimes / extension / cf-bypass / music-api
---

## 总览

| 严重度 | 数量（轮次1+2） | 占比 |
|--------|-----------------|------|
| Critical | 6 | 26% |
| High | 13 | 57% |
| Medium | 4 | 17% |
| **Total** | **23** | — |

## 全部问题清单

| # | 严重度 | 类别 | 问题 | 子项目 |
|---|--------|------|------|--------|
| 001 | critical | security | cf-bypass mirror route 无认证开放代理 (SSRF) | cf-bypass |
| 002 | critical | security | Frontend RSS v-html XSS | frontend |
| 003 | critical | security | Desktop webSecurity: false | desktop |
| 004 | critical | code-smell | SDK ErrorCategory.INTERNAL 不存在 | sdk |
| 005 | high | security | Backend JWT 默认密钥可猜测 | backend |
| 006 | high | architecture | Backend 分层违规（routes 含业务逻辑） | backend |
| 007 | high | architecture | Backend 上帝模块（6+ 文件 500-1330行） | backend |
| 008 | high | architecture | Desktop 上帝模块 + 代码重复 | desktop |
| 009 | high | architecture | Frontend 上帝组件（VideoPlayer 3418行） | frontend |
| 010 | high | code-smell | Frontend 类型侵蚀 + 分层违规 | frontend |
| 011 | high | compliance | SDK 假 stdlib-only 承诺 + 漏依赖 | sdk |
| 012 | high | architecture | Site-runtimes 跨站代码大量重复 | site-runtimes |
| 013 | high | architecture | Bilibili sign.py 上帝模块 | site-runtimes |
| 014 | high | security | Extension 权限过宽 + 多处安全问题 | extension |
| 015 | medium | code-smell | Desktop 常量不统一 + 双 preload | desktop |
| 016 | medium | test | SDK 测试覆盖不足 | sdk |
| **017** | **high** | **architecture** | **Frontend 上帝组件 v2（VideoPlayer 2673行 / RssSources 1941行）** | **frontend** |
| **018** | **high** | **architecture** | **Desktop 上帝模块 v2（youtubei_core 940行 + 3处YouTube重复）** | **desktop** |
| **019** | **high** | **architecture** | **Backend 上帝模块 v2（scheduler 917行 / routes/music 712行）** | **backend** |
| **020** | **high** | **code-smell** | **Frontend 类型侵蚀 + 废弃双份组件** | **frontend** |
| **021** | **high** | **architecture** | **Site-runtimes proxy 三站重复 + 异常使用不当** | **site-runtimes** |
| **022** | **medium** | **code-smell** | **SDK 全局可变状态 + Backend 双引号违规** | **sdk/backend** |
| **023** | **critical** | **security** | **Desktop webSecurity + Extension 权限过宽（未修复）** | **desktop/extension** |

## 建议处理顺序

1. **Critical 安全优先**：023(webSecurity) → 001(SSRF) → 002(XSS) → 003(未完全修复) → 014(extension)
2. **上帝模块拆分**：017(frontend) → 018(desktop) → 019(backend) → 007/009 跟进
3. **代码去重**：021(site-runtimes proxy) → 018(desktop YouTube解析) → 020(frontend 双份组件)
4. **类型/风格修复**：020(any类型) → 022(双引号/全局状态)
