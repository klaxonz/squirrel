---
title: 代码审查汇总 2026-06-07
scope: 全量扫描 — backend / sdk / desktop / frontend / site-runtimes / extension / cf-bypass / music-api
---

## 总览

| 严重度 | 数量 | 占比 |
|--------|------|------|
| Critical | 4 | 25% |
| High | 10 | 62.5% |
| Medium | 2 | 12.5% |
| **Total** | **16** | — |

## 优先级最高的 5 个问题

| # | 严重度 | 类别 | 问题 | 文件 |
|---|--------|------|------|------|
| 1 | critical | security | cf-bypass mirror route 无认证开放代理 (SSRF) | `cf-bypass/.../routes.py:51` |
| 2 | critical | security | Frontend RSS 阅读器 v-html 未消毒导致 XSS | `frontend/.../RssSources.vue:1113` |
| 3 | critical | security | Desktop 主窗口 webSecurity: false | `desktop/src/window.mjs:265` |
| 4 | critical | code-smell | SDK ErrorCategory.INTERNAL 不存在导致运行时崩溃 | `sdk/src/crawl/extractor.py:85` |
| 5 | high | architecture | Backend 分层违规：routes 含业务逻辑+直连DB | `backend/routes/sites.py:24`, `routes/playlist.py:54` |

## 分项目摘要

### Backend (4 个 issue files: #005, #006, #007, + 合并)
- **严重**: JWT_SECRET_KEY 默认值为可猜测的 `'change-me-in-env'`
- **严重**: 三处分层违规（routes/sites.py 业务逻辑、routes/playlist.py 直连DB、routes/music.py 70 个重复 try/except）
- **严重**: `subscription_sync_state_service.py` 等 6+ 个上帝模块（500-1330 行）
- **中**: 3 个 RSS 客户端实现挤在单文件中

### SDK (2 个 issue files: #004, #011, #016)
- **危急**: `ErrorCategory.INTERNAL` 枚举不存在 → 提取异常时 AttributeError 崩溃
- **严重**: "stdlib-only" 假承诺 + `beautifulsoup4` 未声明依赖
- **中**: 测试覆盖严重不足（仅 2 个测试），模块级可变全局状态线程不安全

### Desktop (2 个 issue files: #003, #008, #015)
- **危急**: `webSecurity: false` 关闭所有安全保护
- **严重**: 3 个上帝模块（940/885/756 行）+ 多处代码重复（WBI 签名、escapeXml、缓存、cookie）
- **中**: Chrome 版本 UA 硬编码、缓存 TTL 不统一、双 preload 文件、空 feed 目录、静默吞异常

### Frontend (2 个 issue files: #002, #009, #010)
- **危急**: RSS v-html XSS 漏洞（无 DOMPurify 消毒）
- **严重**: VideoPlayer.vue (3418 行)、RssSources.vue (2962 行) 超级组件
- **严重**: 132+ `any` 类型侵蚀 + 多处分层违规（store 直接调 API、view 绕过 store）

### Site-runtimes (2 个 issue files: #012, #013)
- **严重**: 跨站点代码大量重复（proxy 类 4 站、分页 3 站、load_local_attr 5 站、缩略图 2 站）
- **严重**: bilibili `sign.py` 536 行混合 6+ 种不相关的 Bilibili API 逻辑
- **中**: Pornhub 直接使用 `requests` 绕过 SDK 限速、订阅 404 URL 变异副作用

### Extension + cf-bypass + music-api (2 个 issue files: #001, #014)
- **危急**: cf-bypass mirror route 无认证 + 无白名单 → 开放 SSRF 代理
- **严重**: Extension host_permissions `*://*/*`、token 在 storage.sync、login 通过 HTTP、CSP 不必要地放宽
- **中**: cf-bypass Settings 类永不使用、music-api 是无自定义代码的空壳

## 改进建议

### 1. cf-bypass 安全加固（防火墙优先）
**修复思路：** 加 hostname 白名单控制 SSRF，加 API key 认证保护所有端点，接入 Settings 配置
**参考：** `code-audit-2026-06-07-001-cf-bypass-ssrf-no-auth.md`

### 2. Frontend XSS 修复
**修复思路：** 安装 DOMPurify，所有 v-html 渲染外部内容前消毒
**参考：** `code-audit-2026-06-07-002-frontend-xss-rss-v-html.md`

### 3. Desktop webSecurity 修复
**修复思路：** 移除 `webSecurity: false`，按需放宽已知 CDN 的 CORS
**参考：** `code-audit-2026-06-07-003-desktop-websecurity-disabled.md`

### 4. SDK 运行时崩溃修复
**修复思路：** `ErrorCategory.INTERNAL` → `UNKNOWN` + 声明 beautifulsoup4 依赖
**参考：** `code-audit-2026-06-07-004-sdk-error-category-crash.md`, `code-audit-2026-06-07-011-sdk-false-stdlib-claim-missing-dep.md`

### 5. Backend 分层架构重建
**修复思路：** 迁移 routes/sites.py 业务逻辑到 service、routes/playlist.py DB 查询到 service、music.py 用异常处理器消除重复 try/except
**参考：** `code-audit-2026-06-07-006-backend-architecture-layer-violations.md`

### 6. 上帝模块分解
**修复思路：** subscription_sync_state_service 按责任拆分、VideoPlayer 拆 composable 和子组件、youtubei_core 按领域拆分
**参考：** `code-audit-2026-06-07-007-backend-god-modules.md`, `code-audit-2026-06-07-008-desktop-god-modules-duplication.md`, `code-audit-2026-06-07-009-frontend-god-components.md`

### 7. Site-runtimes 跨站代码合并
**修复思路：** 提取 BaseProxy、BaseHtmlPaginationSubscription 到 SDK，各站点仅提供差异化配置
**参考：** `code-audit-2026-06-07-012-site-runtimes-code-duplication.md`

### 8. Extension 权限瘦身
**修复思路：** 精确化 host_permissions、token 改 storage.local、检测 HTTPS
**参考：** `code-audit-2026-06-07-014-extension-security-issues.md`

### 9. 常量统一整理
**修复思路：** 所有 User-Agent 和缓存 TTL 统一到 constants.mjs，消除重复 preload
**参考：** `code-audit-2026-06-07-015-desktop-constants-preload.md`

### 10. SDK 测试基础设施建设
**修复思路：** 添加核心数据模型序列化、异常体系、限速器的单元测试；考虑 SdkContext 上下文对象消除全局状态
**参考：** `code-audit-2026-06-07-016-sdk-test-coverage-global-state.md`
