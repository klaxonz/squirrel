# Desktop 可观测性修复方案

## 根因
`src/` 下约 15 个文件中大量 `catch {}` 不做任何日志输出，导致生产环境所有播放失敗、登录错误、缓存失效均不可见。

## 修复思路
1. 不引入第三方日志库，直接使用已有的 `console.error`/`console.warn`/`console.debug` 模式（`main.mjs`/`window.mjs` 已有先例）
2. 统一前缀 `[squirrel-desktop]` + 文件名标记
3. 分两类处理：
   - **URL 校验类 catch**（`new URL()` 解析失败 → 返回 false/''）：`console.debug` 级别，正常操作不产生错误日志
   - **操作类 catch**（文件读写、网络请求、JSON 解析）：`console.warn`/`console.error` 级别

## 涉及文件
- `src/cookie-header.mjs` — 7 处 catch
- `src/ipc-handlers.mjs` — 5 处 catch
- `src/site-login.mjs` — 3 处 bare catch
- `src/window-state.mjs` — 1 处
- `src/window.mjs` — 1 处
- `src/search/providers/shared.mjs` — 1 处
- `src/playback/providers/youtube/index.mjs` — 2 处
- `src/playback/providers/youtube/youtubei_core.mjs` — 10+ 处
- `src/playback/providers/youporn/index.mjs` — 2 处
- `src/playback/providers/pornhub/index.mjs` — 1 处

## 风险
- 日志过多可能 clutter 输出：URL 校验类用 `debug` 级别控制
- 不影响现有业务逻辑（只加日志不改变返回值）
