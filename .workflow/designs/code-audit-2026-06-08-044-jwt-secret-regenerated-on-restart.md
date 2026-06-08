# Fix: JWT_SECRET_KEY 随机默认值导致重启后所有会话失效

## 根因
`config.py:42` — `JWT_SECRET_KEY: str = token_urlsafe(32)` 在类定义时（import 时）求值，每次进程启动生成不同密钥，导致所有已签发 JWT 失效。

## 修复思路
移除随机默认值，改为空字符串默认，添加 `@field_validator("JWT_SECRET_KEY")` 在启动时校验非空。这样用户必须通过 `.env` 或环境变量显式设置，不设置则抛清晰错误并阻止启动。

## 涉及文件
- `squirrel-backend/core/config.py` — 改默认值 + 加 validator

## 潜在风险
- 现有部署未设置 `JWT_SECRET_KEY` 的环境变量将启动失败 → 这是预期的行为，只需一次设置即可长期稳定
- `token_urlsafe` 导入不再使用 → 可移除
