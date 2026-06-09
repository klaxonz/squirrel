# Fix: Backend Path Traversal — Log/Cookie/Icon

## 根因

三个位置接收用户输入后直接拼接到文件路径中，未校验路径遍历（`../`）：

1. **`log_service.py:51`** — `filename` query param → `os.path.join(LOG_DIR, filename)`
2. **`cookie_config.py:30-32`** — `site_slug` → 仅 `strip().lower()`，无 `../` 过滤
3. **`site_icons.py:26-39`** — `site_name` → `normalize_site_slug` 仅 strip/lower，无路径校验

## 修复思路

统一使用 `Path.resolve()` + `is_relative_to()` 模式：

```python
resolved = (base_dir / user_input).resolve()
if not resolved.is_relative_to(base_dir.resolve()):
    raise_for_path_escape(...)
```

### 各位置细节

| 位置 | 基准目录 | 超出后行为 |
|------|---------|-----------|
| `log_service.py:51` | `LOG_DIR` (Path) | 返回 `([], 0, False)` |
| `cookie_config.py:30-32` | `get_site_cookies_dir()` | 返回 `default.txt` fallback |
| `site_icons.py:26-39` | `squirrel-site-runtimes/` | 返回 `None` |

## 涉及文件

- `squirrel-backend/services/log_service.py` — 添加 path traversal 检查
- `squirrel-backend/core/cookie_config.py` — 添加 slug 安全校验
- `squirrel-backend/utils/site_icons.py` — 添加 path 安全校验

## 潜在风险

- `is_relative_to()` 是 Python 3.9+，项目 Python 版本需满足
- `cookie_config.py` 中 fallback 到 `default.txt` 可能让攻击探测转为无害路径但不会泄露或写入越界
- 不影响现有功能：所有合法 site_slug 不会包含 `../`
