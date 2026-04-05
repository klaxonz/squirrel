# Sync Center SSE Cookie Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace bearer-token auth with `HttpOnly` cookie auth and make `SyncCenter` update live through browser-native SSE with no polling fallback.

**Architecture:** The backend becomes cookie-auth only, with one new sync-center SSE endpoint that emits full snapshot events for feed, extract, and selected run detail. The frontend removes `localStorage` token handling, relies on cookie-backed authenticated requests, and swaps the `SyncCenter` page from timer-driven refresh to one `EventSource` connection.

**Tech Stack:** FastAPI, Starlette `StreamingResponse`, Redis pub/sub, Vue 3, Axios, native `EventSource`, pytest, Node `node:test`

---

## File Structure

### Backend

- Modify: `squirrel-backend/utils/jwt_helper.py`
  Cookie constants, cookie setters/clearers, token decode helpers, and `get_current_user` move to cookie-based lookup.
- Modify: `squirrel-backend/routes/middleware/auth.py`
  API middleware stops reading `Authorization` headers and validates the auth cookie instead.
- Modify: `squirrel-backend/routes/user.py`
  Login sets the auth cookie, response body stops exposing `access_token`, and a logout route clears the cookie.
- Modify: `squirrel-backend/routes/subscription.py`
  Add `GET /api/subscription/sync-center/stream`.
- Create: `squirrel-backend/services/sync_center_stream_service.py`
  SSE payload formatting, initial snapshot assembly, heartbeat emission, Redis invalidation subscription, and publish helpers.
- Modify: `squirrel-backend/services/video_extraction_center_service.py`
  Add one extraction dashboard snapshot helper for SSE and HTTP reuse.
- Modify: `squirrel-backend/services/subscription_sync_history_service.py`
  Add one run-detail snapshot helper for SSE and drawer reuse.
- Modify: `squirrel-backend/services/subscription_sync_event_service.py`
  Publish feed and run invalidations after sync event projection updates.
- Modify: `squirrel-backend/services/video_extraction_projection_service.py`
  Publish extract invalidations after extraction projection refreshes.
- Create: `squirrel-backend/tests/routes/test_auth_cookie_middleware.py`
  Cookie-only middleware coverage.
- Create: `squirrel-backend/tests/routes/test_user_cookie_auth_routes.py`
  Login/logout cookie contract coverage.
- Create: `squirrel-backend/tests/routes/test_sync_center_stream_route.py`
  SSE route initial event coverage.
- Create: `squirrel-backend/tests/services/test_sync_center_stream_service.py`
  Invalidation publisher and SSE helper coverage.

### Frontend

- Modify: `squirrel-frontend/src/utils/axios.ts`
  Remove bearer header injection and enable cookie-backed requests.
- Modify: `squirrel-frontend/src/utils/auth.ts`
  Remove token-specific storage cleanup and keep redirect helpers.
- Modify: `squirrel-frontend/src/api/users.ts`
  Add logout API.
- Modify: `squirrel-frontend/src/composables/useUser.ts`
  Remove token persistence, add auth-resolution state, and treat `/me` as the source of truth.
- Modify: `squirrel-frontend/src/App.vue`
  Remove `localStorage`-gated user bootstrap.
- Modify: `squirrel-frontend/src/router/index.ts`
  Route guard resolves auth from `/me`, not from a stored token.
- Modify: `squirrel-frontend/src/api/subscriptionSyncCenter.ts`
  Add one helper to build the SSE stream URL.
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
  Remove the page polling timer and apply SSE snapshots directly to the existing refs.
- Create: `squirrel-frontend/test/auth-cookie-cutover.test.mjs`
  Source-level checks for the auth cutover.
- Create: `squirrel-frontend/test/sync-center-event-source-stream.test.mjs`
  Source-level checks for EventSource-based sync-center updates.

## Task 1: Convert Backend Auth Middleware To Cookie-Only

**Files:**
- Create: `squirrel-backend/tests/routes/test_auth_cookie_middleware.py`
- Modify: `squirrel-backend/utils/jwt_helper.py`
- Modify: `squirrel-backend/routes/middleware/auth.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.middleware.auth import AuthMiddleware
from utils.jwt_helper import AUTH_COOKIE_NAME


def _build_app(monkeypatch):
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get('/api/private')
    async def private_api():
        return JSONResponse({'ok': True})

    monkeypatch.setattr('routes.middleware.auth.decode_token', lambda token: {'sub': '7'})
    return app


def test_private_api_accepts_cookie_auth(monkeypatch):
    client = TestClient(_build_app(monkeypatch))
    response = client.get('/api/private', cookies={AUTH_COOKIE_NAME: 'cookie-token'})
    assert response.status_code == 200
    assert response.json() == {'ok': True}


def test_private_api_rejects_bearer_header_without_cookie(monkeypatch):
    client = TestClient(_build_app(monkeypatch))
    response = client.get('/api/private', headers={'Authorization': 'Bearer legacy-token'})
    assert response.status_code == 401
    assert response.json()['msg'] == '请先登录'
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_auth_cookie_middleware.py -q
```

Expected: FAIL because `AuthMiddleware` still looks only at `Authorization` headers and `AUTH_COOKIE_NAME` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

`squirrel-backend/utils/jwt_helper.py`

```python
from fastapi import Cookie, HTTPException, Response, status

AUTH_COOKIE_NAME = 'squirrel_auth'
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/',
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path='/',
        httponly=True,
        secure=True,
        samesite='lax',
    )


async def get_current_user(token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> Optional[User]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    if not token:
        raise credentials_exception
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = int(payload.get('sub'))
    user = user_service.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    from services import user_config_service
    user._cached_config = user_config_service.get_config(user_id)
    return user
```

`squirrel-backend/routes/middleware/auth.py`

```python
from utils.jwt_helper import AUTH_COOKIE_NAME, decode_token


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith('/api') or is_public_api_path(path):
            return await call_next(request)

        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            raise TokenMissingError()

        try:
            decode_token(token)
        except Exception:
            logger.error('Invalid token', exc_info=True)
            raise TokenExpiredError()

        return await call_next(request)
```

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_auth_cookie_middleware.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/utils/jwt_helper.py squirrel-backend/routes/middleware/auth.py squirrel-backend/tests/routes/test_auth_cookie_middleware.py
git commit -m "refactor: switch auth middleware to cookie tokens"
```

## Task 2: Change Login And Logout To Cookie Auth

**Files:**
- Create: `squirrel-backend/tests/routes/test_user_cookie_auth_routes.py`
- Modify: `squirrel-backend/routes/user.py`
- Modify: `squirrel-backend/utils/jwt_helper.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.user import router
from utils.jwt_helper import AUTH_COOKIE_NAME, get_current_user


def _build_client(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(
        'routes.user.user_service.authenticate',
        lambda email, password: (SimpleNamespace(id=7, to_dict=lambda: {'id': 7, 'nickname': 'neo'}), object()),
    )
    monkeypatch.setattr('routes.user.create_access_token', lambda data, expires_delta=None: 'cookie-token')
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, to_dict=lambda: {'id': 7, 'nickname': 'neo'})
    return TestClient(app)


def test_login_sets_auth_cookie_and_hides_access_token(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.post('/api/users/login', json={'email': 'neo@example.com', 'password': 'pw'})

    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data'] == {'user': {'id': 7, 'nickname': 'neo'}}
    assert response.cookies.get(AUTH_COOKIE_NAME) == 'cookie-token'
    assert 'HttpOnly' in response.headers['set-cookie']


def test_logout_clears_auth_cookie(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.post('/api/users/logout')

    assert response.status_code == 200
    assert response.json()['code'] == 0
    assert f'{AUTH_COOKIE_NAME}=' in response.headers['set-cookie']
    assert 'Max-Age=0' in response.headers['set-cookie']
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_user_cookie_auth_routes.py -q
```

Expected: FAIL because `/api/users/login` still returns `access_token` in JSON and `/api/users/logout` does not exist.

- [ ] **Step 3: Write minimal implementation**

`squirrel-backend/routes/user.py`

```python
from fastapi import APIRouter, Depends, Response
from utils.jwt_helper import clear_auth_cookie, create_access_token, get_current_user, set_auth_cookie


@router.post('/login')
async def login(request: UserLoginRequest, response: Response):
    result = user_service.authenticate(str(request.email), request.password)
    if not result:
        return response_module.error('邮箱或密码错误')

    user, account = result
    access_token = create_access_token(
        data={'sub': str(user.id)},
        expires_delta=timedelta(days=30),
    )
    set_auth_cookie(response, access_token)

    return response_module.success(
        data={'user': user.to_dict()},
        msg='登录成功',
    )


@router.post('/logout')
async def logout(response: Response):
    clear_auth_cookie(response)
    return response_module.success(msg='退出成功')
```

If the imported common response module name would shadow the `response: Response` parameter, rename the module import to `response_module`.

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_user_cookie_auth_routes.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/routes/user.py squirrel-backend/tests/routes/test_user_cookie_auth_routes.py squirrel-backend/utils/jwt_helper.py
git commit -m "feat: move login flow to cookie auth"
```

## Task 3: Add Sync Center Snapshot Helpers And SSE Route

**Files:**
- Create: `squirrel-backend/tests/routes/test_sync_center_stream_route.py`
- Create: `squirrel-backend/services/sync_center_stream_service.py`
- Modify: `squirrel-backend/routes/subscription.py`
- Modify: `squirrel-backend/services/video_extraction_center_service.py`
- Modify: `squirrel-backend/services/subscription_sync_history_service.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from routes.subscription import router
from utils.jwt_helper import get_current_user


def test_sync_center_stream_emits_initial_snapshots(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)

    async def _fake_stream(*, user_id, selected_run_id):
        yield 'event: feed_snapshot\\ndata: {"overview":{"running_count":1}}\\n\\n'
        yield 'event: extract_snapshot\\ndata: {"overview":{"running_count":2}}\\n\\n'
        yield 'event: run_detail\\ndata: {"run":{"run_id":"run-7"},"events":[]}\\n\\n'

    monkeypatch.setattr('routes.subscription.sync_center_stream_service.stream_sync_center_events', _fake_stream)

    client = TestClient(app)
    with client.stream('GET', '/api/subscription/sync-center/stream', params={'selectedRunId': 'run-7'}) as response:
        body = ''.join(response.iter_text())

    assert response.status_code == 200
    assert 'event: feed_snapshot' in body
    assert 'event: extract_snapshot' in body
    assert 'event: run_detail' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_sync_center_stream_route.py -q
```

Expected: FAIL because the stream route and `sync_center_stream_service` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

`squirrel-backend/services/video_extraction_center_service.py`

```python
EXTRACTION_PREVIEW_LIMIT = 40


def get_extraction_dashboard_snapshot(user_id: int, *, preview_limit: int = EXTRACTION_PREVIEW_LIMIT) -> dict:
    overview = get_extraction_center_overview(user_id)
    running_preview = list_extraction_center_items(user_id, 'running', None, None, 1, preview_limit).data
    queued_preview = list_extraction_center_items(user_id, 'queued', None, None, 1, preview_limit).data
    recent_preview = list_extraction_center_items(user_id, 'recent', None, None, 1, preview_limit).data
    return {
        'overview': overview,
        'runningPreview': running_preview,
        'queuedPreview': queued_preview,
        'recentPreview': recent_preview,
    }
```

`squirrel-backend/services/subscription_sync_history_service.py`

```python
def get_run_detail_snapshot(run_id: str, user_id: int) -> dict | None:
    run = get_run_detail(run_id, user_id)
    if not run:
        return None
    return {
        'run': run,
        'events': list_run_events(run_id, user_id),
    }
```

`squirrel-backend/services/sync_center_stream_service.py`

```python
import json

from services import subscription_sync_center_service, subscription_sync_history_service, video_extraction_center_service


def encode_sse_event(event_name: str, payload: dict) -> str:
    return f'event: {event_name}\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n'


async def stream_sync_center_events(*, user_id: int, selected_run_id: str | None):
    yield encode_sse_event('feed_snapshot', subscription_sync_center_service.get_feed_dashboard_snapshot(user_id, None, None, None, None))
    yield encode_sse_event('extract_snapshot', video_extraction_center_service.get_extraction_dashboard_snapshot(user_id))
    if selected_run_id:
        snapshot = subscription_sync_history_service.get_run_detail_snapshot(selected_run_id, user_id)
        if snapshot:
            yield encode_sse_event('run_detail', snapshot)
    yield encode_sse_event('heartbeat', {'ok': True})
```

`squirrel-backend/routes/subscription.py`

```python
from starlette.responses import StreamingResponse
from services import sync_center_stream_service


@router.get('/api/subscription/sync-center/stream')
async def stream_sync_center(
    selected_run_id: str | None = Query(None, alias='selectedRunId'),
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        sync_center_stream_service.stream_sync_center_events(
            user_id=current_user.id,
            selected_run_id=selected_run_id,
        ),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-store',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_sync_center_stream_route.py -q
```

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/routes/subscription.py squirrel-backend/services/sync_center_stream_service.py squirrel-backend/services/video_extraction_center_service.py squirrel-backend/services/subscription_sync_history_service.py squirrel-backend/tests/routes/test_sync_center_stream_route.py
git commit -m "feat: add sync center sse stream route"
```

## Task 4: Publish Feed, Extract, And Run Invalidations

**Files:**
- Create: `squirrel-backend/tests/services/test_sync_center_stream_service.py`
- Modify: `squirrel-backend/services/sync_center_stream_service.py`
- Modify: `squirrel-backend/services/subscription_sync_event_service.py`
- Modify: `squirrel-backend/services/video_extraction_projection_service.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services import subscription_sync_event_service, sync_center_stream_service, video_extraction_projection_service


def test_append_event_publishes_feed_and_run_invalidations(monkeypatch):
    published = []

    monkeypatch.setattr(
        sync_center_stream_service,
        'publish_sync_center_invalidation',
        lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(subscription_sync_event_service, 'build_event', lambda event_input, session=None: SimpleNamespace(stream_id='run-7'))

    class DummySession:
        def add(self, value):
            pass

        def flush(self):
            pass

    event_input = subscription_sync_event_service.SyncEventInput(
        stream_id='run-7',
        subscription_id=7,
        sync_mode='incremental',
        event_type='started',
    )

    subscription_sync_event_service.append_event(event_input, session=DummySession(), project=False)

    assert ('squirrel:sync-center:feed', None) in published
    assert ('squirrel:sync-center:run', {'run_id': 'run-7'}) in published


def test_refresh_projection_for_task_publishes_extract_invalidation(monkeypatch):
    published = []

    monkeypatch.setattr(
        sync_center_stream_service,
        'publish_sync_center_invalidation',
        lambda channel, payload=None: published.append((channel, payload)),
    )
    monkeypatch.setattr(video_extraction_projection_service, '_refresh_projection_group', lambda *args, **kwargs: None)

    task = SimpleNamespace(task_type='video_extract', subscription_id=9, payload={'run_id': 'run-9'})
    video_extraction_projection_service.refresh_projection_for_task(task, session=object())

    assert ('squirrel:sync-center:extract', {'run_id': 'run-9'}) in published
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/services/test_sync_center_stream_service.py -q
```

Expected: FAIL because no invalidation publisher is wired yet.

- [ ] **Step 3: Write minimal implementation**

`squirrel-backend/services/sync_center_stream_service.py`

```python
from core.cache import create_redis_client

SYNC_CENTER_FEED_CHANNEL = 'squirrel:sync-center:feed'
SYNC_CENTER_EXTRACT_CHANNEL = 'squirrel:sync-center:extract'
SYNC_CENTER_RUN_CHANNEL = 'squirrel:sync-center:run'


def publish_sync_center_invalidation(channel: str, payload: dict | None = None) -> None:
    client = create_redis_client()
    client.publish(channel, json.dumps(payload or {}, ensure_ascii=False))
```

`squirrel-backend/services/subscription_sync_event_service.py`

```python
from services import subscription_sync_projection_service, subscription_sync_run_service, sync_center_stream_service


def append_event(event_input: SyncEventInput, *, session=None, project: bool = True) -> SubscriptionSyncEvent:
    if session is not None:
        event = build_event(event_input, session=session)
        session.add(event)
        session.flush()
        if project:
            subscription_sync_projection_service.apply_event(event, session=session)
        sync_center_stream_service.publish_sync_center_invalidation(sync_center_stream_service.SYNC_CENTER_FEED_CHANNEL)
        sync_center_stream_service.publish_sync_center_invalidation(
            sync_center_stream_service.SYNC_CENTER_RUN_CHANNEL,
            {'run_id': event.stream_id},
        )
        return event
    with get_session() as managed_session:
        return append_event(event_input, session=managed_session, project=project)
```

`squirrel-backend/services/video_extraction_projection_service.py`

```python
from services import sync_center_stream_service


def refresh_projection_for_task(task: CrawlTask, *, session: Optional[Session] = None) -> None:
    if task.task_type != VIDEO_EXTRACT_TASK_TYPE or task.subscription_id is None:
        return
    group_kind, group_value = _derive_group_key(task)
    if session is not None:
        _refresh_projection_group(session, subscription_id=int(task.subscription_id), group_kind=group_kind, group_value=group_value)
        sync_center_stream_service.publish_sync_center_invalidation(
            sync_center_stream_service.SYNC_CENTER_EXTRACT_CHANNEL,
            {'run_id': task.payload.get('run_id') if task.payload else None},
        )
        return
    with get_session() as managed_session:
        refresh_projection_for_task(task, session=managed_session)
```

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/services/test_sync_center_stream_service.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/services/sync_center_stream_service.py squirrel-backend/services/subscription_sync_event_service.py squirrel-backend/services/video_extraction_projection_service.py squirrel-backend/tests/services/test_sync_center_stream_service.py
git commit -m "feat: publish sync center realtime invalidations"
```

## Task 5: Remove Frontend Bearer Tokens And Bootstrap Auth From `/me`

**Files:**
- Create: `squirrel-frontend/test/auth-cookie-cutover.test.mjs`
- Modify: `squirrel-frontend/src/utils/axios.ts`
- Modify: `squirrel-frontend/src/utils/auth.ts`
- Modify: `squirrel-frontend/src/api/users.ts`
- Modify: `squirrel-frontend/src/composables/useUser.ts`
- Modify: `squirrel-frontend/src/App.vue`
- Modify: `squirrel-frontend/src/router/index.ts`

- [ ] **Step 1: Write the failing test**

```javascript
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8')

test('frontend auth cutover removes token persistence and bearer injection', async () => {
  const axiosSource = await read('../src/utils/axios.ts')
  const userSource = await read('../src/composables/useUser.ts')
  const appSource = await read('../src/App.vue')
  const routerSource = await read('../src/router/index.ts')

  assert.match(axiosSource, /withCredentials:\s*true/)
  assert.doesNotMatch(axiosSource, /Authorization/)
  assert.doesNotMatch(userSource, /localStorage\.setItem\('token'/)
  assert.doesNotMatch(appSource, /localStorage\.getItem\('token'/)
  assert.doesNotMatch(routerSource, /localStorage\.getItem\('token'/)
  assert.match(userSource, /const hasResolvedAuth = ref\(false\)/)
  assert.match(userSource, /const result = \(await getUserMe\(\)\)/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-frontend`:

```bash
node --test test/auth-cookie-cutover.test.mjs
```

Expected: FAIL because the frontend still injects bearer headers and reads `localStorage`.

- [ ] **Step 3: Write minimal implementation**

`squirrel-frontend/src/utils/axios.ts`

```typescript
const instance = axios.create({
  timeout: 60000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use((config) => config)
```

`squirrel-frontend/src/api/users.ts`

```typescript
export const logoutUser = async () => {
  return post('/api/users/logout')
}
```

`squirrel-frontend/src/composables/useUser.ts`

```typescript
const hasResolvedAuth = ref(false)

const login = async (data: Record<string, unknown>) => {
  loading.value = true
  error.value = null

  const result = (await loginUser(data)) as ApiResult<AuthResult>
  if (!result.error) {
    currentUser.value = result.data?.user || null
    isAuthenticated.value = !!result.data?.user
    hasResolvedAuth.value = true
  }
  loading.value = false
  error.value = result.error
  return result
}

const getCurrentUser = async () => {
  loading.value = true
  error.value = null

  const result = (await getUserMe()) as ApiResult<User>
  if (result.error?.status === 401) {
    currentUser.value = null
    isAuthenticated.value = false
  } else if (!result.error) {
    currentUser.value = result.data || null
    isAuthenticated.value = true
  }
  hasResolvedAuth.value = true
  loading.value = false
  error.value = result.error
  return result
}
```

`squirrel-frontend/src/App.vue`

```vue
onMounted(async () => {
  const configResult = await loadSystemConfig()
  if (configResult.error) {
    Logger.error('Failed to load system config', configResult.error)
  }
  syncAppTopbarHeight()
})
```

`squirrel-frontend/src/router/index.ts`

```typescript
router.beforeEach(async (to, from, next) => {
  const { getCurrentUser, hasResolvedAuth, isAuthenticated } = useUser()

  if (!hasResolvedAuth.value) {
    const result = await getCurrentUser()
    if (result.error?.status && result.error.status !== 401) {
      Logger.error('Failed to get user info', result.error)
    }
  }

  if (to.meta.requiresAuth !== false && !isAuthenticated.value) {
    next('/login')
    return
  }
  if ((to.path === '/login' || to.path === '/register') && isAuthenticated.value) {
    next('/')
    return
  }

  next()
})
```

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-frontend`:

```bash
node --test test/auth-cookie-cutover.test.mjs
```

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-frontend/src/utils/axios.ts squirrel-frontend/src/utils/auth.ts squirrel-frontend/src/api/users.ts squirrel-frontend/src/composables/useUser.ts squirrel-frontend/src/App.vue squirrel-frontend/src/router/index.ts squirrel-frontend/test/auth-cookie-cutover.test.mjs
git commit -m "refactor: remove frontend bearer token auth"
```

## Task 6: Replace Sync Center Polling With One EventSource Connection

**Files:**
- Create: `squirrel-frontend/test/sync-center-event-source-stream.test.mjs`
- Modify: `squirrel-frontend/src/api/subscriptionSyncCenter.ts`
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

- [ ] **Step 1: Write the failing test**

```javascript
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const read = async (relativePath) => readFile(new URL(relativePath, import.meta.url), 'utf8')

test('sync center is driven by one EventSource stream instead of a polling timer', async () => {
  const apiSource = await read('../src/api/subscriptionSyncCenter.ts')
  const viewSource = await read('../src/views/SyncCenter.vue')

  assert.match(apiSource, /export const getSyncCenterStreamUrl = \(/)
  assert.match(apiSource, /\/api\/subscription\/sync-center\/stream/)
  assert.match(viewSource, /let dashboardStream: EventSource \| null = null/)
  assert.match(viewSource, /new EventSource\(getSyncCenterStreamUrl\(/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('feed_snapshot'/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('extract_snapshot'/)
  assert.match(viewSource, /dashboardStream\.addEventListener\('run_detail'/)
  assert.doesNotMatch(viewSource, /const DASHBOARD_POLL_INTERVAL = 15000/)
  assert.doesNotMatch(viewSource, /setInterval\(/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-frontend`:

```bash
node --test test/sync-center-event-source-stream.test.mjs
```

Expected: FAIL because `SyncCenter.vue` still uses a page-level timer.

- [ ] **Step 3: Write minimal implementation**

`squirrel-frontend/src/api/subscriptionSyncCenter.ts`

```typescript
export const getSyncCenterStreamUrl = (selectedRunId?: string | null) => {
  const params = new URLSearchParams()
  if (selectedRunId) {
    params.set('selectedRunId', selectedRunId)
  }
  const query = params.toString()
  return query ? `/api/subscription/sync-center/stream?${query}` : '/api/subscription/sync-center/stream'
}
```

`squirrel-frontend/src/views/SyncCenter.vue`

```typescript
import { useUser } from '@/composables/useUser'
import { getSyncCenterStreamUrl } from '@/api'
import { logoutAndRedirect } from '@/utils/auth'

const { getCurrentUser } = useUser()
let dashboardStream: EventSource | null = null

const closeDashboardStream = () => {
  if (!dashboardStream) {
    return
  }
  dashboardStream.close()
  dashboardStream = null
}

const openDashboardStream = () => {
  closeDashboardStream()
  dashboardStream = new EventSource(getSyncCenterStreamUrl(selectedRunId.value))

  dashboardStream.addEventListener('feed_snapshot', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    overview.value = snapshot.overview
    runningPreview.value = snapshot.runningPreview || []
    queuedPreview.value = snapshot.queuedPreview || []
    feedRecentRuns.value = snapshot.recentRuns || []
  })

  dashboardStream.addEventListener('extract_snapshot', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    extractionOverview.value = snapshot.overview
    extractionRunningPreview.value = snapshot.runningPreview || []
    extractionQueuedPreview.value = snapshot.queuedPreview || []
    extractionRecentItems.value = snapshot.recentPreview || []
  })

  dashboardStream.addEventListener('run_detail', (event) => {
    const snapshot = JSON.parse((event as MessageEvent).data)
    historySelectedRun.value = snapshot.run || null
    historyEvents.value = snapshot.events || []
  })

  dashboardStream.onerror = async () => {
    const result = await getCurrentUser()
    if (result.error?.status === 401) {
      logoutAndRedirect()
    }
  }
}

onMounted(() => {
  setPollingEnabled(false)
  setHistoryPollingEnabled(false)
  setExtractionPollingEnabled(false)
  syncFeedRecentWindow()
  openDashboardStream()
})

watch(selectedRunId, () => {
  openDashboardStream()
})

onBeforeUnmount(() => {
  closeDashboardStream()
})
```

Do not keep `DASHBOARD_POLL_INTERVAL`, `refreshDashboard`, or `startDashboardPolling`.

- [ ] **Step 4: Run test to verify it passes**

Run from `squirrel-frontend`:

```bash
node --test test/sync-center-event-source-stream.test.mjs
```

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add squirrel-frontend/src/api/subscriptionSyncCenter.ts squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/test/sync-center-event-source-stream.test.mjs
git commit -m "feat: stream sync center updates over sse"
```

## Task 7: Run Cross-Project Verification And Final Cleanup

**Files:**
- Modify: `squirrel-backend/tests/routes/test_sync_center_stream_route.py`
- Modify: `squirrel-frontend/test/auth-cookie-cutover.test.mjs`
- Modify: `squirrel-frontend/test/sync-center-event-source-stream.test.mjs`

- [ ] **Step 1: Run focused backend tests**

Run from `squirrel-backend`:

```bash
pipenv run pytest tests/routes/test_auth_cookie_middleware.py tests/routes/test_user_cookie_auth_routes.py tests/routes/test_sync_center_stream_route.py tests/services/test_sync_center_stream_service.py -q
```

Expected: PASS with all focused realtime/auth tests green.

- [ ] **Step 2: Run focused frontend tests**

Run from `squirrel-frontend`:

```bash
node --test test/auth-cookie-cutover.test.mjs test/sync-center-event-source-stream.test.mjs
```

Expected: PASS with both source-level regression tests green.

- [ ] **Step 3: Run frontend typecheck**

Run from `squirrel-frontend`:

```bash
npm run typecheck
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 4: Perform manual verification**

1. Log in from a clean browser session.
2. Confirm no `token` entry is created in browser `localStorage`.
3. Open `/sync-center`.
4. Trigger one manual subscription refresh.
5. Confirm feed lanes update without waiting 15 seconds.
6. Confirm extract lane updates as extraction tasks move.
7. Open a run drawer and confirm new events appear live.
8. Log out and confirm protected routes redirect back to `/login`.

- [ ] **Step 5: Commit final cleanup if any verification-only edits were required**

```bash
git add squirrel-backend/tests/routes/test_sync_center_stream_route.py squirrel-frontend/test/auth-cookie-cutover.test.mjs squirrel-frontend/test/sync-center-event-source-stream.test.mjs
git commit -m "test: tighten cookie auth and sse regression coverage"
```

## Self-Review

### Spec coverage

- Cookie-only auth cutover is covered by Task 1, Task 2, and Task 5.
- Native SSE stream route and snapshot contract are covered by Task 3.
- Redis invalidation publishing is covered by Task 4.
- `SyncCenter` polling removal is covered by Task 6.
- Cross-project verification and user-visible checks are covered by Task 7.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every code-changing task includes concrete file paths, commands, and code snippets.

### Type consistency

- Cookie constant name stays `AUTH_COOKIE_NAME`.
- Backend realtime helper file stays `services/sync_center_stream_service.py`.
- Frontend stream URL helper stays `getSyncCenterStreamUrl`.
- Route query parameter stays `selectedRunId`.
