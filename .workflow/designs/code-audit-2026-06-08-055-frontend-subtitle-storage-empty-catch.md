# Fix: usePlayer.ts 空 catch {} 静默丢弃 localStorage 错误

## 根因

`saveSubtitleStyleToStorage()` 中 `catch {}` 静默丢弃所有 `localStorage.setItem()` 异常。

## 修复思路

改为 `catch (err) { console.warn('[SPPlayer] Failed to save subtitle style', err) }`，保持静默安全的同时提供错误日志可观测性。

## 涉及文件

- `squirrel-frontend/src/components/video-player/runtime/usePlayer.ts:161`

## 潜在风险

无。console.warn 不影响运行时行为。
