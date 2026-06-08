# 修复方案：清理死代码和未使用依赖

## 根因

项目演进过程中积累了大量不再使用的模块和依赖，审计报告部分夸大了范围。

## 真实死代码范围（已验证）

| 条目 | 处理方式 |
|------|---------|
| `models/request_log.py` | 删除文件 |
| `queues/queue_monitor.py` | 保留（测试依赖），移除未使用的全局单例 |
| `pytubefix`, `js2py`, `pipdeptree`, `bilibili-api-python`, `cloudscraper`, `sse-starlette`, `phub` | 从 Pipfile 删除 |
| `axios`, `bgutils-js`, `jsdom`, `proxy-agent` | 从 desktop `package.json` 删除 |
| `lodash`, `lodash-es`, `mitt` | 从 frontend `package.json` 删除 |

## 涉及文件

- `squirrel-backend/models/request_log.py` — 删除
- `squirrel-backend/queues/queue_monitor.py` — 移除未使用的 `queue_monitor` 单例
- `squirrel-backend/Pipfile` — 移除 7 个依赖
- `squirrel-desktop/package.json` — 移除 4 个依赖
- `squirrel-frontend/package.json` — 移除 3 个依赖

## 潜在风险

- `request_log.py` 的 Alembic 迁移表定义不受影响（迁移是独立的）
- `queue_monitor.py` 的 test 导入依然有效
- `lodash` 等在 `vite.config.ts` 字符串引用 — 确认安全
