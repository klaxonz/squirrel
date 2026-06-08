# Fix 027 — Python Docstring Language Convention

关联: `.opencode/issues/code-style-2026-06-07-027-python-docstring-language.md`

## 根因

项目无 docstring 语言约定，导致 backend（中文）、SDK（英文）、site-runtimes（混合）不一致。

## 修复思路

1. **AGENTS.md** 增加 docstring 语言约定
2. **自定义检查脚本** `scripts/check-docstring-lang.py` — 用 `ast` 解析 docstring，通过 CJK 字符范围检测语言，按子目录执行规则：
   - `squirrel-backend/` → 中文（现状保持）
   - `squirrel-sdk/` → 英文
   - `squirrel-site-runtimes/` → 英文
3. **AGENTS.md 构建与测试** 节更新 lint 命令，加入脚本调用

## 涉及文件

- `AGENTS.md` — 增加约定 + 更新 lint 命令
- `scripts/check-docstring-lang.py` — 新脚本
- `squirrel-backend/pyproject.toml` — 可选：启用部分 D 规则
- `squirrel-sdk/pyproject.toml` — 同上

## 潜在风险

- 脚本仅检测目录级约定，不强制全局统一
- 当前代码中有大量 docstring，脚本只报告不修改
- CI 集成后需维护规则列表
