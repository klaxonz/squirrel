# 修复方案: 废弃子包/空目录/残缺包清理

## 根因
项目演进过程中遗留的空包裹、空目录和 crash 残留，缺少 `__init__.py` 的包目录。

## 修复思路
1. **删除** `core/exceptions/` — 空包裹，无引用
2. **保留** `core/repository/` — 含有效 BaseRepository CRUD 基类，非废弃
3. **删除** `models/task/` — 空包裹（`__init__.py` 0 字节），无引用
4. **删除** `common/types/` — 空目录，无引用
5. **添加** `consumer/__init__.py` — `consumer.processors` 已有代码，缺父包
6. **添加** `sql/__init__.py` — `sql.subscription_sql` 被外部导入，缺包
7. **删除** `processes/*.tmp` — 10 个 0 字节 crash 残留

## 涉及文件
- `squirrel-backend/core/exceptions/__init__.py` — 删除目录
- `squirrel-backend/models/task/__init__.py` — 删除目录
- `squirrel-backend/common/types/` — 删除空目录
- `squirrel-backend/consumer/__init__.py` — 新建
- `squirrel-backend/sql/__init__.py` — 新建
- `squirrel-backend/processes/*.tmp` — 删除 10 个文件

## 潜在风险
- 极低：`consumer/` 和 `sql/` 添加 `__init__.py` 可能改变 Python 包扫描行为，但当前已是隐式 namespace package，显式化更安全
- `models/task/` 删除后如有 Alembic 或动态扫描引用会报错（经 grep 确认无引用）
