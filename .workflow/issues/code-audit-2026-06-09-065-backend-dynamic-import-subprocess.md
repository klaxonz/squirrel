---
title: Backend Runtime Bridge Dynamic Import — importlib.import_module 注入风险
status: open
severity: low
category: security
location: squirrel-backend/site_runtimes/runtime_bridge.py:70-84; squirrel-backend/site_runtimes/process_launcher.py:106-118
---

## 问题描述

`runtime_bridge.py:70-84` 通过 `importlib.import_module(module_name)` 动态导入模块，`module_name` 来自 `--entrypoint` CLI 参数。虽然不直接从 HTTP 请求可达（通过 subprocess 启动），但 `entrypoint` 来源于站点目录/配置数据。

`process_launcher.py:106-118` 的 `subprocess.Popen` 使用 `# noqa: S603` 抑制了 Bandit 警告，但 `command` 参数含有 `record.entrypoint`、`record.data_path` 等用户配置数据。

另外 `runtime_bridge.py:249-251` 将 `--import-path` 参数直接插入 `sys.path[0]`，允许加载任意路径下的 Python 模块。

## 影响

需要站点目录配置被篡改才能利用，攻击面有限。但在多租户或插件市场中，恶意插件可通过自定义 entrypoint 执行任意代码。

## 建议方向

- 对 `entrypoint` 进行白名单校验（只允许已知模块名格式）
- `--import-path` 限制为预配置目录
- 在 process_launcher 中记录所有动态导入的完整参数用于审计