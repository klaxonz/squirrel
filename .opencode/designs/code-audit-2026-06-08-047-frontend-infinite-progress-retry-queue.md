# 047: BackendPlayerAdapter 无限重试队列修复

## 根因
`flushPending()` catch 块无条件将失败项推回 `pendingProgress`，无重试计数。

## 修复思路
1. 为 `pendingProgress` 项添加 `retryCount` 属性（用类型扩展）
2. 达到 3 次后 `playerLogger.warn` 并丢弃
3. 保留现有 `slice(-20)` 作为二次防护

## 涉及文件
- `squirrel-frontend/src/components/video-player/core/BackendPlayerAdapter.ts`

## 风险
低——纯内存逻辑，不涉及 API 行为变更。
