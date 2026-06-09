# Fix: Backend 默认数据库密码 — POSTGRES_PASSWORD 默认 postgres

## 根因

`core/config.py:31` 中 `POSTGRES_PASSWORD` 直接硬编码默认值为 `"postgres"`，Pydantic Settings 类没有对该字段做任何校验。同时，`COOKIECLOUD_PASSWORD`、`KUGOU_MUSIC_COOKIE`、`KUGOU_MUSIC_API_BASE_URL` 等敏感配置默认为空字符串，使用时静默失败无提示。

## 修复思路

1. **POSTGRES_PASSWORD validator** — 参照 `JWT_SECRET_KEY` 的现有模式，添加 `field_validator`，在非 dev 环境下拒绝默认值 `"postgres"`
2. **启动时日志警告** — 在 `model_post_init` 中对 `COOKIECLOUD_PASSWORD`、`KUGOU_MUSIC_API_BASE_URL`、`KUGOU_MUSIC_COOKIE` 为空时打印 warning 日志，帮助运维人员发现配置缺失

## 涉及文件

- `squirrel-backend/core/config.py` — 新增 validator + post_init 检查

## 潜在风险

- 已有的 dev 环境会使用默认密码连接本地 postgres，需要确保 ENV=dev 时 validator 放行
- 日志警告需避免敏感信息泄露（只提示未配置，不打印值）
- 确保 `is_dev` / `environment` 属性在 validator 执行时可访问（validator 在 `__init__` 时执行，`environment` 属性依赖 `os.getenv("ENV")`，没问题）
