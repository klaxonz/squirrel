# Fix #022: SDK 全局可变状态 + Backend 双引号

## 根因

1. **SDK 全局状态**：`http.py` 3 个模块级变量、`utils.py` 2 个模块级变量通过 setter 函数修改，测试间无法自动隔离
2. **SDK docstring 中英文混用**：`http.py` 中 `request()`、`request_without_limit()`、`get()`、`post()`、`configure_cloudflare_bypass_client()` docstring 为中文
3. **Backend 双引号**：7 个文件约 800+ 处使用 `"` 而非 `'`，无 ruff quote 规则约束

## 修复思路

### Part 1: SDK 全局状态 — 添加 reset 函数（最小改动）
- `http.py` 新增 `_reset_http_module_state()`：重置 3 个全局变量到初始值
- `utils.py` 新增 `_reset_utils_module_state()`：重置 2 个 cookie 解析器到 None
- `runtime_http.reset_runtime_http_state()` 改为调用上述函数，不再直接访问 SDK 私有属性
- 不影响外部 API，只为测试隔离提供统一入口

### Part 2: SDK docstring 统一为英文
- 修改 `http.py` 中 5 个函数的 docstring 从中文→英文

### Part 3: Backend 双引号→单引号
- `pyproject.toml` 添加 `[tool.ruff.format] quote-style = "single"`
- 对 7 个文件运行 `ruff format`

## 涉及文件

| 文件 | 改动 |
|------|------|
| `squirrel-sdk/src/crawl/http.py` | 加 `_reset_http_module_state()`，docstring 英文化 |
| `squirrel-sdk/src/crawl/utils.py` | 加 `_reset_utils_module_state()` |
| `squirrel-backend/utils/runtime_http.py` | 改用 SDK reset 函数 |
| `squirrel-backend/pyproject.toml` | 加 quote-style 配置 |
| `squirrel-backend/services/video_extraction_center_service.py` | ruff format 修正引号 |
| `squirrel-backend/services/video_list_service.py` | 同上 |
| `squirrel-backend/services/video_list_query_service.py` | 同上 |
| `squirrel-backend/services/video_history_service.py` | 同上 |
| `squirrel-backend/utils/metrics.py` | 同上 |
| `squirrel-backend/services/youtube_oauth_service.py` | 同上 |
| `squirrel-backend/utils/cookie.py` | 同上 |

## 潜在风险

- `ruff format` 可能引入额外格式化变更（缩进、换行等），需 review diff
- SDK reset 函数需确保不破坏当前测试的 save/restore 逻辑
