# Sync Center 卡片进度展示简化设计

## 背景
- 同步中心中列与右列卡片右侧的百分比信息价值偏低。
- Feed 中列进度条目前大量依赖阶段映射值，不能准确代表真实进度。

## 设计结论
- 移除中列运行卡片右侧百分比。
- 移除 Feed 中列运行卡片的进度条。
- 移除右列“刚处理完”卡片右侧百分比。
- 保留阶段标签、状态标签、时间文案和数量指标，优先表达“当前在做什么、产出了多少、还剩多少”。

## 影响范围
- `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`
- `squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue`
- `squirrel-frontend/src/components/sync-center/SyncRecentTaskBoard.vue`

## 验证
- 运行相关前端测试，确认组件可渲染且卡片信息结构正常。
