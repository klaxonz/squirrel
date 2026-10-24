# Squirrel 重构计划

## Overview

以未发布产品为前提，对 Squirrel 单仓库进行结构性重构。目标不是保留旧实现，而是减少跨层耦合、删除重复装配和无意义兼容代码，并让后端、Electron 主进程、Vue 渲染器各自拥有清晰边界。每个切片都必须保持启动路径可验证。

## 当前基线

- 仓库包含 Python/FastAPI 后端、Electron 主进程、Vue/TypeScript 渲染器、浏览器扩展和 Cloudflare sidecar。
- 后端已有 domains/application/infrastructure/shared_kernel 分层和较完整 pytest 覆盖；不重新发明 Clean Architecture。
- 桌面端已有模块化文件，但 `src/main.mjs` 仍混合进程启动、窗口生命周期、媒体 session、播放预热和环境解析。
- 渲染器已有 feature/shared/app 分层、Pinia、Vue Query 和 Vitest；先从真实数据边界审计，不盲目迁移组件。

## Architecture Decisions

- 后端保留现有领域目录；把 FastAPI 装配细节拆成 application-owned modules，`app.py` 只负责组装。
- Electron 主进程按职责拆出 runtime configuration、application lifecycle、media setup 和 playback warmup；不引入容器或事件总线。
- 渲染器的远程数据统一通过既有 API client + Vue Query；Pinia 只保留真正的客户端状态，逐步移除重复请求状态。
- 兼容性不作为约束。迁移时直接删除旧入口、旧别名和已无调用方的转发层，但只删除有证据确认无引用的代码。
- 不新增生产依赖，除非现有依赖和标准库无法满足明确需求。

## 实施结果

- RSS 业务由 `RssAccountService`、`RssSyncService` 和 `RssService` 显式组合；HTTP 依赖从 `app.state` 获取应用级实例。
- RSS 旧模块级 service singleton 与转发入口已删除，测试通过 dependency override 注入替身。
- 音乐主页专辑查询共用一个 loader，避免重复请求状态和错误处理实现。

## Task List

### Phase 1: 后端装配边界

- [x] 将异常处理协议移出 application/app.py
- [x] 将路由与静态资源注册移出 application/app.py
- [x] 简化 FastAPI app factory 并保持启动行为

### Checkpoint: 后端装配

- [x] 后端应用测试通过
- [x] 后端静态检查通过
- [x] `/health` 和异常响应行为保持可验证

### Phase 2: Electron 主进程边界

- [x] 提取渲染器 URL 与进程环境配置
- [x] 提取窗口生命周期与单实例行为
- [x] 提取媒体 session 与播放预热初始化
- [x] 删除 main.mjs 中已被提取流程

### Checkpoint: 桌面主进程

- [x] Electron 单元测试通过
- [x] renderer 构建和类型检查通过
- [x] Electron 启动 smoke test 通过

### Phase 3: 渲染器数据边界

- [x] 盘点 API client、query composable 和 Pinia 重复职责
- [x] 选择一个主链路完成 query/mutation 边界收敛（音乐主页专辑查询）
- [x] 清理对应旧请求状态和无调用方 helper（专辑 loader 重复实现）

### Checkpoint: 渲染器

- [x] Vitest 通过
- [x] 类型检查、lint 和构建通过
- [x] 主链路运行时 smoke test 通过

### Phase 4: 收尾审查

- [x] 运行后端与桌面完整验证命令
- [x] 进行正确性、架构、安全、性能审查
- [x] 清理确认无引用的死代码和生成物
- [x] 更新必要的架构说明

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| 后端路由导入顺序影响启动 | High | 保留显式有序 tuple，先迁移装配函数，再运行应用测试 |
| Electron 初始化时序改变 | High | 先提取纯配置和纯函数，再拆生命周期；保留启动 smoke test |
| Vue Query 与 Pinia 状态重复导致行为回归 | Medium | 先盘点实际调用方，只迁移一个垂直主链路 |
| 工作区已有本地文件或生成物 | Medium | 不回滚用户修改；只触碰计划声明的源码和测试 |

## Verification Commands

- Backend: `cd squirrel-backend && pipenv run pytest`
- Backend lint: `cd squirrel-backend && pipenv run ruff check .`
- Desktop unit: `cd squirrel-desktop && npm test`
- Renderer tests: `cd squirrel-desktop && npm run test:renderer`
- Renderer typecheck/build: `npm run typecheck && npm run build:renderer`
