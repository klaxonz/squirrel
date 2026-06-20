# 后端代码最佳实践审计报告

> 审计目标：识别所有"最小改动"思维留下的妥协痕迹，推动向"最佳改动"迁移
> 审计范围：`squirrel-backend/` 全量后端代码
> 审计人：Reasonix Code  
> 日期：2025-07-09

---

## 目录

1. [审计方法论](#1-审计方法论)
2. [🔴 严重问题——运行时必出 Bug](#2-严重问题运行时必出-bug)
3. [🟠 架构问题——违背 DDD / 最佳实践](#3-架构问题违背-ddd--最佳实践)
4. [🟡 次级问题——维护性 / 可测试性](#4-次级问题维护性--可测试性)
5. [🔵 模式亮点——值得保持的做法](#5-模式亮点值得保持的做法)
6. [修复路线图](#6-修复路线图)

---

## 1. 审计方法论

### 1.1 分析过程

审计分 6 轮扫描，每轮聚焦一个维度：

| 轮次 | 维度 | 工具与方法 | 覆盖文件数 |
|---|---|---|---|
| 1 | 项目骨架 | `read_file` 主入口、app 组装、lifespan | 6 |
| 2 | ORM 模型层 | `explore` 子 agent 扫描全部 domain models | 25 个模型 |
| 3 | 应用服务层 | `explore` 子 agent 分析 service 模式 | 30+ 服务 |
| 4 | 基础设施层 | 逐个阅读 database/config/http/extraction | 20+ 文件 |
| 5 | 调度与消息 | 深入 scheduling、messaging、worker 体系 | 15+ 文件 |
| 6 | 交叉验证 | 对可疑模式做 `search_content` 确认影响面 | 全量 |

### 1.2 评判标准

每个问题按三级评定：

- **🔴 严重**：运行时必然出 Bug 或数据不正确
- **🟠 架构**：违背 DDD、SOLID、或 Python 最佳实践，长期不可维护
- **🟡 次级**：可测试性 / 可读性 / 一致性问题，可逐步优化

---

## 2. 🔴 严重问题——运行时必出 Bug

### 2.1 `not` 在 SQLAlchemy WHERE 子句中作为 Python 布尔值

**文件：** `squirrel-backend/domains/subscription/application/services/core/crud.py:36-41`

```python
def get_active_user_subscription_by_url(self, user_id: int, url: str) -> Subscription:
    with self.session_factory() as session:
        subscription = session.execute(
            select(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url == url,
                not Subscription.is_deleted,         # ← Bug
                UserSubscription.user_id == user_id,
                not UserSubscription.is_deleted,     # ← Bug
            ),
        ).scalar_one_or_none()
        return subscription
```

#### 分析过程

1. 阅读 `Subscription` 模型（`subscription.py`）发现 `is_deleted: Mapped[bool]` 是布尔列
2. 对比同文件中其他查询（如 `get_active_user_subscription_url_map` 在第 53 行使用 `.is_(False)`）发现写法不一致
3. 查阅 SQLAlchemy 2.0.49（来自 `Pipfile`）的文档确认：`ColumnElement.__bool__` 在 SQLAlchemy 2.x 中会**抛出 `TypeError`**，提示 "Cannot use boolean value on SQL expression"
4. 行 53 使用 `Subscription.is_deleted.is_(False)` 是正确的写法，证明团队知道正确做法，但行 37-40 漏改了

**根本原因：** 这是从 SQLAlchemy 1.x 迁移到 2.x 时，`not` 写法未被全部扫描替换。Python 的 `not` 作用于 Column 对象时：
- 在 SQLAlchemy 1.x 中：Column 是 truthy → `not True` = `False` → 过滤条件退化为无意义的 `WHERE False`，**永远不会返回任何行**（等同于下面 2.2 条的正确写法被破坏）
- 在 SQLAlchemy 2.x 中：Column 的 `__bool__` 抛出 `TypeError` → 调用方如果没捕获就崩溃

**最佳改动：**

```python
~Subscription.is_deleted,           # 使用 SQL 取反运算符
UserSubscription.user_id == user_id,
~UserSubscription.is_deleted,
```

或使用 `.is_()` 方法：

```python
Subscription.is_deleted.is_(False),
UserSubscription.is_deleted.is_(False),
```

**影响面：** 轻微——只有 `get_active_user_subscription_by_url` 一个调用点。但这个方法用于检查用户订阅的活跃状态，返回错误结果会影响订阅相关的显示和业务逻辑。

---

### 2.2 错误的导入路径（运行时 ImportError）

**文件：** `squirrel-backend/domains/subscription/application/services/core/crud.py:152-153`

```python
def update_subscription(self, subscription_id: int, update_data: dict[str, Any]) -> bool:
    ...
    import user.services.search.suggestion_service as search_suggestion_service
    search_suggestion_service.invalidate_users_for_subscription(subscription_id)
    return updated
```

#### 分析过程

1. 行 152 使用 `import user.services.search.suggestion_service`——这个路径看起来像 Python 顶层模块
2. 搜索全库确认：`search_content("invalidate_users_for_subscription")` 返回两处——定义在 `domains/user/application/services/search/suggestion_service.py:83`，调用在此
3. `search_files("user/services")` 返回空——顶层不存在 `user/` 目录
4. `search_files("domains/user")` 返回空（因为这是文件内容搜索模式不对），但 `list_directory` 确认 `domains/user/` 存在
5. 同文件其他导入全部使用 `from domains.xxx` 风格（如行 27 `from domains.subscription.domain.junctions...`）
6. **结论：** 这是一个从上一次代码重构/目录迁移中遗漏的导入路径，运行时此方法返回前会抛 `ModuleNotFoundError`

**最佳改动：**

```python
from domains.user.application.services.search.suggestion_service import (
    invalidate_users_for_subscription,
)
```

并且可以将 `update_subscription` 改为接收该服务作为构造器参数（若想让 `SubscriptionCrudService` 不依赖 user 领域）。

**影响面：** 任何触发 `update_subscription` 的 HTTP 请求都会 500 崩溃。该方法是订阅列表中的"更新订阅信息"功能的核心路径。

---

## 3. 🟠 架构问题——违背 DDD / 最佳实践

### 3.1 SerializerMixin —— ORM 模型里塞序列化逻辑

**文件：** `squirrel-backend/infrastructure/database/mixins.py:7-117`

#### 分析过程

1. 发现 `Base`（`base.py`）是裸的 `DeclarativeBase`，所有模型通过继承 `SerializerMixin` 获得 `to_dict()`、`from_dict()`
2. 通过 `explore` 全量扫描 domain models 确认：25 个模型中有 24 个使用了 `SerializerMixin`，唯一跳过的是 `VideoCreator`（一个纯 M:N 表）
3. 追踪 `to_dict()` 的调用链：在 `detail_loader.py:61` 中有 `**video.to_dict()`、在 `page_loader.py` 中有 `video_list.append({...})` 手动构造字典
4. 查看 `_serialize_value`：datetime 被格式化为 `'%Y-%m-%d %H:%M:%S'`，**时区信息被丢弃**
5. 对比业界最佳实践：所有现代的 FastAPI 项目都使用 Pydantic schemas 做序列化边界，ORM 模型不应有序列化方法

#### 问题清单

| 问题 | 具体表现 | 影响 |
|---|---|---|
| **响应形状不可控** | 给 `Video` 模型加个字段，所有用 `to_dict()` 的接口自动多一个响应字段 | 版本兼容性灾难 |
| **时区信息丢失** | `_serialize_value` 将 datetime → `'%Y-%m-%d %H:%M:%S'` | 前端无法判断 UTC/本地 |
| **复合类型不可控** | `extra_data` 的 JSON 内容可能递归序列化，也可能丢 | 响应结构不确定 |
| **循环引用风险** | `nested=True` 时关系可能形成循环 | 栈溢出 |

#### 最佳改动

1. 删除 `SerializerMixin` 类
2. 为每个接口响应定义 Pydantic schema

```python
# domains/video/interfaces/dto/video_response.py
from pydantic import BaseModel, field_serializer
from datetime import datetime

class VideoResponse(BaseModel):
    id: int
    title: str
    url: str
    thumbnail: str | None = None
    duration: int | None = None
    publish_date: datetime | None = None
    # ... 只暴露需要的字段

    @field_serializer('publish_date')
    def serialize_datetime(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.isoformat()  # 保留时区信息
```

3. 在 service 层或 interface 层做 `Video → VideoResponse` 映射

**影响面：** 大。约 15+ 个 `to_dict()` 调用点需替换。但这是**一次性的、可逐步进行的**迁移——可以先为新接口只用 Pydantic schema，旧接口逐步替换。

---

### 3.2 `get_current_user` 泄露原始 ORM 模型到 HTTP 层

**文件：** `squirrel-backend/domains/user/application/services/auth.py:30-33`

```python
async def get_current_user(token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> User:
    """Validate token and return current user with config preloaded"""
    _, user = validate_auth_token(token)
    user._cached_config = user_config_service.get_config(user.id)
    return user
```

#### 分析过程

1. `User` 是 SQLAlchemy ORM 模型（继承 `Base, SerializerMixin`），不是 Pydantic model
2. FastAPI 的 `Depends(get_current_user)` 将这个原始 ORM 对象注入到所有需要认证的路由中
3. 当路由直接返回这个对象时，FastAPI 会尝试序列化它的**所有属性**——包括 `token_version`、以及通过 `Account` 关联可达的 `credential`（密码哈希）
4. 更糟的是：`_cached_config` 作为动态绑定属性，它的存在依赖于 `get_current_user` 被调用——如果有代码路径绕过了它直接 `session.get(User, user_id)`，就没有 `_cached_config`

#### 最佳改动

```python
# domains/user/interfaces/dto/user_dto.py
class UserDto(BaseModel):
    id: int
    nickname: str
    avatar: str | None = None
    model_config = ConfigDict(from_attributes=True)

# domains/user/application/services/auth.py
async def get_current_user(...) -> UserDto:
    _, user = validate_auth_token(token)
    return UserDto.model_validate(user)
```

**影响面：** 所有 `current_user.id` / `current_user.nickname` 引用仍然可以正常工作（通过 `from_attributes`），但额外属性的访问会在编译期/运行时明确暴露出来。

---

### 3.3 依赖注入有名无实——全量模块级单例

#### 分析过程

通过 `explore` 扫描了 30+ 个服务文件，总结出两种模式：

```python
# 模式 A（视频 / 用户领域，约 80%）：构造器注入 + 默认值
class VideoCrudService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

video_crud_service = VideoCrudService()   # 模块级单例

# 模式 B（订阅领域，约 20%）：构造参数默认值是函数本身
class SubscriptionCrudService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory
```

两种模式都支持注入，但**生产代码从未使用注入能力**：

- HTTP 路由中：`get_db` 依赖从未传给 service
- Service 单例在模块加载时实例化，无法替换
- 多请求间共享同一个 session factory（虽然是 context manager，但连接池可能被互相影响）

测试倒是可以利用注入——但生产代码只是空有形式。

#### 最佳改动

```python
# domains/video/interfaces/http/dependencies.py
def get_video_crud_service(db: Session = Depends(get_db)) -> VideoCrudService:
    """每个请求获得可独立控制的 service 实例"""
    return VideoCrudService(session_factory=lambda: db)
```

路由改为：

```python
@router.get('/videos/{id}')
def get_video(
    id: int,
    svc: VideoCrudService = Depends(get_video_crud_service),
    user: UserDto = Depends(get_current_user),
):
    ...
```

---

### 3.4 无领域异常层次

#### 分析过程

搜索全库中 `raise ValueError(` 的出现：

- `crud.py:68` — `raise ValueError('url is required')`
- `crud.py:70` — `raise ValueError('title is required')`
- `user/service.py:41` — `raise ValueError('邮箱已被注册')`
- `user/service.py:84` — `raise ValueError('当前密码错误')`
- ...

这些都是业务规则违规，但全部裸抛 `ValueError`。HTTP 层统一 `except ValueError` 无法区分：

- 参数缺失 → 应该 400
- 业务冲突 → 应该 409
- 资源不存在 → 应该 404

#### 最佳改动

```python
# shared_kernel/domain/exceptions.py
class DomainError(Exception):
    """All domain exceptions inherit from this."""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)

class ResourceNotFoundError(DomainError):
    def __init__(self, message: str = '资源不存在'):
        super().__init__(message, code=404)

class ConflictError(DomainError):
    def __init__(self, message: str = '资源冲突'):
        super().__init__(message, code=409)
```

统一处理：

```python
# application/app.py
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.code,
        content={'code': exc.code, 'msg': exc.message},
    )

_EXCEPTION_HANDLERS = {
    ...
    DomainError: domain_error_handler,
}
```

---

### 3.5 推迟导入解决循环依赖——模块分层不对

#### 分析过程

`crud.py` 中的 `_upsert_video_safe`：

```python
def _upsert_video_safe(video_id: int) -> None:
    try:
        from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
        get_meili_video_indexer().upsert_safe(video_id)
    except Exception:
        logger.warning(...)
```

同理，`_index_video_after_commit` 也放在 `crud.py` 中，然后 `video_persistence.py` 又有一份同构的 `_index_video_after_commit`。

搜索 `from x import` 在函数体内的所有出现：

- `crud.py:44` — `from domains.video.application.services.search.meili_indexer import ...`
- 多处 `from infrastructure.site_catalog.cloudflare_bypass import get_default_client`

这些"函数内部 import"说明模块分层让顶层的 import 会形成循环。正确做法是：**领域服务不应直接依赖搜索索引器**。

#### 最佳改动

引入事件层或使用已存在的 `register_after_commit` 机制做观察者模式：

```python
# infrastructure/events/after_video_saved.py
class AfterVideoSaved:
    """视频保存后的事件——监听者负责索引、通知等副作用"""
    _listeners: list[Callable[[int], None]] = []

    @classmethod
    def register(cls, listener: Callable[[int], None]):
        cls._listeners.append(listener)

    @classmethod
    def fire(cls, video_id: int):
        for listener in cls._listeners:
            try:
                listener(video_id)
            except Exception:
                logger.exception('Event listener failed')

# 在 bootstrap 中注册
AfterVideoSaved.register(lambda vid: get_meili_video_indexer().upsert_safe(vid))
```

---

### 3.6 Model `to_dict()` 和 `detail_loader` 中 `**video.to_dict()` 的不安全展开

**文件：** `squirrel-backend/domains/video/application/services/listing/detail_loader.py:61`

```python
return {
    **video.to_dict(),           # ← 展开 model 的所有字段到响应
    'thumbnail': ...,
    'interaction_type': ...,
    ...
}
```

这等同于"model 的每个字段都是 API 响应承诺的一部分"。如果某天 Video 模型加了 `internal_debug_info` 字段，它就会出现在 API 响应中。这是最小改动（"先返回再说"）而非最佳改动（"定义契约"）。

---

## 4. 🟡 次级问题——维护性 / 可测试性

### 4.1 `register_after_commit` 中的错误守卫

**文件：** `squirrel-backend/infrastructure/database/session.py:49-51`

```python
def register_after_commit(session, callback) -> None:
    if not hasattr(session, 'info'):
        callback()          # ← 立即执行！绕过事务边界
        return
```

如果 session 没有 `info` 属性（什么情况下会这样？），回调会**在事务提交前立即执行**。此时如果 `session.close()` 先被调用，回调尝试访问已关闭的 session 会抛异常。但如果 `close()` 在回调之后才调用（当前 `finally` 块中的顺序），回调就能访问到一个尚未提交的、可能被回滚的 session。

影响：Meilisearch 索引更新可能在事务未提交或已回滚时执行，导致索引中存在数据库中不存在的视频记录。

**最佳改动：** 删除这个有问题的守卫，让缺乏 `info` 属性的场景直接在 `session.info.setdefault(...)` 处抛异常暴露出来：

```python
def register_after_commit(session, callback) -> None:
    """Register a callback to run after the current transaction commits."""
    session.info.setdefault(AFTER_COMMIT_CALLBACKS_KEY, []).append(callback)
```

---

### 4.2 `Scheduler._run_jobs` 使用 `time.sleep(1)` 轮询且线程不可中断

**文件：** `squirrel-backend/infrastructure/scheduling/engine.py:40-50`

```python
while self.running:
    current_time = time.time()
    with self._lock:
        jobs_snapshot = self.jobs[:]
    for job in jobs_snapshot:
        if job['next_run'] <= current_time:
            ...
    time.sleep(1)              # ← 不可中断
```

问题：调用 `stop()` 后如果 `running` 设置为 `False` 时刚好进入 `sleep`，最坏情况需要 1 秒才能响应。且 `self.running` 的读写没有用 `self._lock` 保护——存在竞态条件。

**最佳改动：**

```python
import threading

def __init__(self):
    self.jobs = []
    self._stop_event = threading.Event()

def _run_jobs(self):
    while not self._stop_event.is_set():
        current_time = time.time()
        ...
        self._stop_event.wait(timeout=1)   # 可中断

def stop(self):
    self._stop_event.set()
```

---

### 4.3 调度器线程以 daemon 模式运行，关机无协调

- `engine.py` 中的 `_run_jobs` 线程是 `daemon=False`（未显式设置，默认非 daemon）√ — 但 `_run_job_with_trace` 启动的子线程是 `daemon=True`
- `store.py` 中的 `execute_task_now` 启动的线程 `daemon=True`
- `lifecycle.py` 中的 `_heartbeat_thread` 也是 `daemon=True`

进程退出时，daemon 线程被**强制终止**。如果它恰好在写数据库或更新 Redis，可能造成数据损坏：

```python
# store.py:166-168
thread = Thread(
    target=self._execute_task_with_logging,
    kwargs={...},
)
thread.daemon = True     # ← 进程退出时强制杀掉
thread.start()
```

**最佳改动：** 维护线程注册表，退出时逐个 join：

```python
class ThreadManager:
    _threads: list[Thread] = []

    @classmethod
    def start_daemon(cls, target, name=None):
        t = Thread(target=target, name=name, daemon=True)
        t.start()
        cls._threads.append(t)
        return t

    @classmethod
    def shutdown_all(cls, timeout=5):
        for t in cls._threads:
            t.join(timeout=timeout)
```

---

### 4.4 `ScheduledTaskService` 使用静态方法 + 直接 `get_session()`

```python
class ScheduledTaskService:
    @staticmethod
    def create_task(...) -> ScheduledTask | None:
        ...
        with get_session() as session:   # ← 硬编码
```

同文件中有 `def __init__(self, session_factory=None)` 构造器，但 `create_task`、`update_task`、`delete_task` 全部定义为 `@staticmethod` 并硬编码调用 `get_session()`。这是不一致的——部分方法是实例方法，部分是静态方法。

**最佳改动：** 统一为实例方法，通过构造器注入 session factory。

---

### 4.5 VideoPersistenceService 使用裸 `get_session()` 而非注入

```python
class VideoPersistenceService:
    def create_or_update(self, ...):
        with get_session() as session:   # ← 硬编码
```

而视频领域其他服务（`VideoCrudService`、`VideoHistoryService`）都使用了构造器注入模式。这是**不一致**的。

**最佳改动：**

```python
class VideoPersistenceService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def create_or_update(self, ...):
        with self._session_factory() as session:
```

---

### 4.6 `WorkerRunner` 是无操作空壳——最小改动的典型遗迹

**文件：** `squirrel-backend/infrastructure/messaging/framework/runner.py`

文档字符串原文：

> No-op queue worker runner.
> The Redis-Stream consumer half of the message queue was never wired to any
> handler in production ... It is retained as a no-op so the worker process
> entrypoint and its test stay unchanged.

这是"最小改动"的典型症状：旧的生产者/消费者框架解了一半，消费者被删掉了，但空壳保留着"因为测试不崩"。最佳改动应该是：

1. 删除 `WorkerRunner` 类
2. 更新 `workers/messaging/process.py` 中引用它的代码
3. 删除或更新相关测试

---

### 4.7 `SchedulerTaskSynchronizer._get_task_fingerprint` 使用 `getattr` 而非类型化访问

```python
@staticmethod
def _get_task_fingerprint(task) -> tuple:
    return (
        bool(getattr(task, 'is_active', False)),
        int(getattr(task, 'interval', 0)),
        str(getattr(task, 'unit', '')),
        bool(getattr(task, 'start_immediately', False)),
    )
```

`task` 参数没有类型提示。如果传入了错误的类型，`getattr` 会安静地返回默认值而不会报错——指纹改变但不会被发现。

**最佳改动：**

```python
from infrastructure.scheduling.models.scheduled_task import ScheduledTask

@staticmethod
def _get_task_fingerprint(task: ScheduledTask) -> tuple:
    return (
        task.is_active,
        task.interval,
        task.unit,
        task.start_immediately,
    )
```

---

### 4.8 DB 缺少外键约束

通过 `explore` 扫描发现 25 个模型中有 `ForeignKey` 声明的仅有 `CrawlTask` 和 `CrawlJob`。其他"外键"（如 `user_id`、`video_id`、`subscription_id`）都是裸的 `Integer` 列：

```python
# UserSubscription
user_id: Mapped[int] = mapped_column(Integer, nullable=False)
subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
```

没有 `ForeignKey('user.id')`，没有 `ondelete='CASCADE'`。这意味着：

- 删除 user 时，关联的 `UserSubscription`、`VideoHistory`、`VideoInteraction` 成为孤儿数据
- 数据库层面无法保证引用完整性

**最佳改动：** 对已知关联列加上 `ForeignKey` 约束，并通过 Alembic migration 添加。

---

### 4.9 对比同一域内的不一致设计

| 对比项 | Subscription 领域 | Video 领域 | User 领域 |
|---|---|---|---|
| Session 注入 | `__init__(self, session_factory=get_session)` | `__init__(self, session_factory=None)` + 默认 | `__init__(self, session_factory=None)` + 默认 |
| CRUD 服务命名 | `SubscriptionCrudService` | `VideoCrudService` | `UserService` |
| DTO 使用 | 有 `SubscriptionDto`（sqlalchemy_to_pydantic） | 混合使用 `to_dict()` + 手写 dict | 基本没有 DTO |
| 事件解耦 | 领域内 `register_after_commit` + Meilisearch | 同名函数在 `crud.py` 和 `video_persistence.py` 各有一份 | 没有用 |

三个团队（或三次开发周期）对"怎么做"的理解不一致。

---

## 5. 🔵 模式亮点——值得保持的做法

### 5.1 DDD 领域划分清晰

```
domains/
  video/        — 视频管理
  subscription/ — 订阅管理
  user/         — 用户管理
  playlist/     — 播放列表
  rss/          — RSS 订阅
  system/       — 系统配置
  music/        — 音乐功能
```

每个领域有独立的 `application/`、`domain/`、`infrastructure/`、`interfaces/` 分层。这是一个**正确的 DDD 架构骨架**，问题只在具体实现层面。

### 5.2 `viewonly=True` 的谨慎选择

所有 `relationship()` 声明都使用了 `viewonly=True`，意味着 ORM 关系仅用于查询，不用于级联写操作。这避免了 SQLAlchemy ORM 最常见的"自动写"陷阱：

```python
videos: Mapped[list[Video]] = relationship(
    'Video',
    secondary='subscription_video',
    ...
    viewonly=True,       # ← 正确
)
```

### 5.3 构造器注入模式本身（虽未被充分利用）

```python
class VideoCrudService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session
```

虽然生产代码未充分利用，但这个模式本身是正确的——它让测试可以注入 mock session factory。这是"最佳改动"的**基础**，只是没有被**贯彻到底**。

### 5.4 `register_after_commit` 机制

虽然实现有瑕疵（见 4.1），但这个设计思路（事务提交后才触发副作用）是正确的。它避免了在事务中间就发索引更新/通知。

### 5.5 使用 `StrEnum` 定义状态字段

```python
class SyncStatus(StrEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
```

替代了魔数/字符串常量，提升了代码可读性。

---

## 6. 修复路线图

### Phase 1（立即修复 · 影响线上正确性）

| 优先级 | 问题 | 改动量 | 风险 |
|---|---|---|---|
| P0 | 2.1 `not is_deleted` → `~is_deleted` | 1 行 | 低——修复后查询语义正确 |
| P0 | 2.2 导入路径修复 | 1 行 | 低——修复后 update_subscription 返回正常 |

### Phase 2（架构加固 · 影响数据安全和可维护性）

| 优先级 | 问题 | 改动量 | 风险 |
|---|---|---|---|
| P1 | 4.1 `register_after_commit` 守卫修复 | 3 行 | 中——改变回调执行时机 |
| P1 | 3.6 `get_current_user` 返回 DTO | 中（DTO + 所有路由适配） | 中——需检查所有 `current_user.xxx` 引用 |
| P2 | 3.4 领域异常层次 | 中（异常类 + 替换所有 raise ValueError） | 低——向后兼容 |
| P2 | 4.5 VideoPersistenceService 注入修复 | 5 行 | 低 |
| P2 | 4.4 ScheduledTaskService 统一为实例方法 | 20 行 | 低 |

### Phase 3（长期重构 · 影响 API 契约和测试能力）

| 优先级 | 问题 | 改动量 | 风险 |
|---|---|---|---|
| P2 | 3.1 删除 SerializerMixin 迁移到 Pydantic | 大（15+ 调用点） | 中——需逐个接口验证 |
| P2 | 3.3 DI 从模块单例改为 FastAPI Depends | 大（所有路由） | 中——需验证 session 生命周期 |
| P3 | 3.5 事件层解耦消除函数内 import | 中（事件总线 + 监听器） | 中——架构变动 |
| P3 | 4.3 线程管理器 + 优雅关机 | 中 | 低 |
| P3 | 4.8 添加 DB FK 约束 | 大（Alembic migration） | 高——需要验证数据完整性 |
| P3 | 4.6 删除 WorkerRunner | 小 | 低 |
| P3 | 4.2 Scheduler 轮询改为 Event-based | 中 | 低 |
| P3 | 4.7 getattr → 类型化访问 | 多处 | 低 |
