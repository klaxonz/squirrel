---
title: 后端服务层 DI 重构 — 降低测试对 mock 的过度依赖
status: active
created: 2026-06-07
---

# 需求：后端服务层 DI 重构

## 背景

后端 89 个测试文件共使用 1190 次 mock/patch/monkeypatch。根因是服务层采用模块级过程式代码 + 全局单例模式，没有依赖注入，测试无法通过构造函数注入 mock，只能 monkeypatch 模块级全局状态。

已有显式垫片（`subscription_sync_state_service/__init__.py`）专门为了 monkeypatch 能工作而设计，说明团队已意识到问题但未根治。

## 目标

1. 将服务层从模块级过程式函数重构为基于类的构造函数注入模式
2. 引入 `fastapi.Depends` 作为 DI 容器
3. 增加测试基础设施（conftest.py、共享 fixtures、网络层 mock 库）
4. 以 music_service（最高 mock：163 处）为试点完成第一轮重构

## 范围

**Phase 1（本需求）：**
- `squirrel-backend/services/music/` — 重构为基于类的 DI
- `squirrel-backend/tests/services/test_music_service.py` — 重写测试
- `squirrel-backend/tests/conftest.py` — 新建共享 fixtures
- `squirrel-backend/Pipfile` — 增加测试依赖
- 其他文件只做调用处适配

**后期 Phase（不在本需求）：**
- subscription_service 等其余服务
- 全量测试迁移

## 验收标准

- [ ] music service 所有模块使用类 + 构造函数注入（不再直接访问模块级 `_http_client`/`redis_client`/`settings`）
- [ ] `test_music_service.py` mock 数从 163 降至 < 30
- [ ] 测试使用 `respx` mock HTTP 层（而非 mock 业务方法）
- [ ] 所有现有测试通过
- [ ] ruff check 通过
- [ ] 不影响 API 行为（路由层无感知）

## 红线

- 不改路由层（`routes/`）
- 不改数据库模型（`models/`）
- 不改 SDK / 插件 / 前端 / 桌面端

## 关联

- Issue: `.opencode/issues/code-audit-2026-06-07-036-test-heavy-mocking.md`
