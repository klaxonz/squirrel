# 需求 / 缺陷看板

本仓库使用两类轻量看板：

- `requirements-board.md`：追踪需求从收集、排期到完成
- `defects-board.md`：追踪缺陷从发现、定位到修复

这套看板是 **repo-local** 的，适合通过 PR 一起维护；同时仓库也提供了 GitHub Issue 模板，方便把新条目先收集成 issue，再同步到看板。

## 目录

- `docs/boards/requirements-board.md`
- `docs/boards/defects-board.md`
- `.github/ISSUE_TEMPLATE/requirement.yml`
- `.github/ISSUE_TEMPLATE/defect.yml`

## 推荐状态流转

统一状态：

- `Intake`：刚进入看板，待补充或待分诊
- `Ready`：已明确，等待执行
- `In Progress`：正在处理
- `Blocked`：被依赖或决策阻塞
- `Done`：已完成或已关闭

## 推荐标签

如果使用 GitHub Issues，建议在仓库里创建这些标签：

- `type:requirement`
- `type:defect`
- `status:intake`
- `status:ready`
- `status:in-progress`
- `status:blocked`
- `status:done`
- `priority:p0`
- `priority:p1`
- `priority:p2`
- `severity:critical`
- `severity:high`
- `severity:medium`
- `severity:low`

## 使用约定

### 需求看板

适合记录：

- 新功能
- 体验改进
- 技术能力建设
- 流程性改进

每条需求尽量包含：

- 简短标题
- 优先级
- 验收标准
- 关联 issue / PRD / PR

### 缺陷看板

适合记录：

- 已确认的 bug
- 回归问题
- 线上故障
- 已知但暂未修复的问题

每条缺陷尽量包含：

- 严重级别
- 复现方式
- 影响范围
- 关联 issue / PR / 修复提交

## 使用建议

已进入 `Ready` 的需求可以直接关联 GitHub issue、PRD 文档或实现 PR。

也就是说：

- 看板负责 **收集与排期**
- 关联文档和 PR 负责 **记录实现与验收**
