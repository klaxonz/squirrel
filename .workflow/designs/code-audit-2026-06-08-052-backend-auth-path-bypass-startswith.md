# Auth 中间件路径匹配绕过修复方案

## 根因

`is_public_api_path()` 对 `PUBLIC_PATH_PREFIXES` 使用 `str.startswith()` 匹配，导致：
- `/api/users/login_malicious` 匹配到 `/api/users/login`
- `/health/readyanything` 匹配到 `/health/ready`
- `/health_bad` 匹配到 `/health`

## 修复思路

将 PUBLIC_PATH_PREFIXES 拆为两类：

1. **精确路径**（`PUBLIC_EXACT_PATHS`）：使用 `path == target` 精确匹配
   - `/api/users/login`, `/api/users/register`, `/docs`, `/redoc`, `/openapi.json`, `/api/video/thumbnail`

2. **前缀路径**（`PUBLIC_PATH_PREFIXES`）：使用 `path == prefix or path.startswith(prefix + "/")` 确保路径分隔符
   - `/health`, `/health/ready`, `/health/live`

`/api/sites/*/icon` 模式匹配逻辑不变。

## 涉及文件

- `routes/middleware/auth.py` — 修改 `is_public_api_path` 逻辑
- `tests/routes/test_auth_middleware.py` — 补充 bypass 用例

## 潜在风险

- `/api/video/thumbnail` 改为精确匹配后，若实际有子路径（如 `/api/video/thumbnail/123`）会不再匹配。经查代码，无此类子路径，安全。
- `/health` 前缀匹配带分隔符，`/health`、`/health/`、`/health/ready` 均匹配，`/health_bad` 不匹配，符合预期。
