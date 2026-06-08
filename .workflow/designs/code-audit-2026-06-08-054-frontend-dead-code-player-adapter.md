# Fix: BackendPlayerAdapter 死代码清理

## 根因
- `syncTimer` 字段（L6）是早期实现残留，实际定时器引用为 `syncTimerHandle`（L30），从未读写
- 空 catch-rethrow（原 L242-244）已在 commit `edd13c3d` 修复为带重试的 catch

## 修复思路
1. 仅移除 L6 未使用的 `syncTimer` 字段声明

## 涉及文件
- `squirrel-frontend/src/components/video-player/core/BackendPlayerAdapter.ts`

## 潜在风险
- 无。纯删除未使用字段，不影响运行时行为
