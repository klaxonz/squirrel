---
title: 'Desktop: 多个上帝模块 + 大量重复代码'
severity: high
category: code-smell
location: squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs, src/search/providers/remote-channel.mjs, src/site-login.mjs
---

## 问题描述

### 上帝模块

| 文件 | 行数 | 混合职责 |
|------|------|---------|
| `youtubei_core.mjs` | 940 | OAuth 流管理 + PoToken 生成 + 播放列表解析 + 字幕获取 + 格式标准化 + DASH manifest 构建 + 缓存 |
| `remote-channel.mjs` | 885 | 5 个站点（YouTube/Bilibili/JavDB/Pornhub/YouPorn）的频道/演员页面解析 |
| `site-login.mjs` | 756 | 5 个站点的登录状态检查 + 登录窗口管理 + cookie 构建 |
| `ipc-handlers.mjs` (installDesktopBridgeHandlers) | 256 | 安装 16 个 IPC handler，混合播放/搜索/登录/窗口/服务器配置 |

### 重复代码

| 模式 | 位置 |
|------|------|
| WBI signing 密钥表 + getMixinKey | `bilibili/request-runtime.mjs` + `remote-channel.mjs`（20 行完全一致） |
| escapeXml 函数 | `youtube/index.mjs` + `bilibili/index.mjs` |
| 缓存 TTL / cache-scope 逻辑 | youtube、bilibili、pornhub 各独立实现一套 |
| mergeCookieHeaders | `cookie-header.mjs` + `adult-page.mjs`（不同实现） |
| extractAttribute 辅助 | 4 个搜索 provider 文件各有一份 |

## 影响

- 新增站点需修改 god 模块，冲突风险高
- WBI 签名密钥变更需同步两处，否则无声失败
- 缓存行为不一致，调试困难

## 建议方向

1. `youtubei_core.mjs` → 拆为 `oauth.mjs`、`playback-resolver.mjs`、`captions.mjs`、`youtubei_core.mjs`（轻量编排）
2. `remote-channel.mjs` → 按站点拆分为独立模块，共享 WBI 签名
3. `site-login.mjs` → 按站点拆分为独立登录 provider
4. 抽取 WBI 签名到 `src/shared/bilibili-sign.mjs`
5. 抽取 `escapeXml`、`mergeCookieHeaders`、`extractAttribute` 到共享工具
6. 创建通用 `PlaybackCache` 类在 `src/playback/providers/shared/`
