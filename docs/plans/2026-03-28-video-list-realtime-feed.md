# Video List Realtime Feed Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the default realtime video list fast by reading from a maintained `user_video_feed` table instead of recomputing visibility from joins on every request.

**Architecture:** Add a transactional projection table keyed by `(user_id, subscription_id, video_id)`, keep it in sync from subscription and extraction write paths, and rewrite the list query to page from that table before fetching current-page detail rows.

**Tech Stack:** FastAPI, SQLAlchemy ORM/Core, PostgreSQL, Alembic, pytest

---

### Task 1: Add failing tests for the new feed-driven list behavior

**Files:**
- Modify: `squirrel-backend/tests/services/test_video_service.py`
- Modify: `squirrel-backend/tests/services/test_subscription_service.py`

**Step 1: Write failing tests**

- Add a `list_videos` test that seeds `user_video_feed`, `video`, `subscription`, `video_history`, and creator data, then asserts:
  - page results come back in publish-date order
  - `last_position` is filled from the current user's history
  - `subscriptions` come from the current user's visible subscriptions
- Add a subscription-service test that proves unsubscribe removes the user's feed rows.

**Step 2: Run tests to verify failure**

Run:

```bash
cd squirrel-backend
pytest tests/services/test_video_service.py tests/services/test_subscription_service.py -q
```

Expected: failures because `user_video_feed` does not exist in code paths yet.

### Task 2: Add the feed model and migration

**Files:**
- Create: `squirrel-backend/models/user_video_feed.py`
- Create: `squirrel-backend/alembic/versions/20260328_add_user_video_feed_projection.py`

**Step 1: Add model**

- Define `UserVideoFeed` with:
  - `user_id`
  - `subscription_id`
  - `video_id`
  - `publish_date`
  - `video_created_at`
  - `domain`
  - `is_nsfw`
  - timestamps
- Add uniqueness and read-path indexes.

**Step 2: Add migration**

- Create table and indexes
- Backfill from `user_subscription + subscription_video + video + subscription`

### Task 3: Add realtime feed maintenance helpers

**Files:**
- Create: `squirrel-backend/services/user_video_feed_service.py`
- Modify: `squirrel-backend/services/subscription_service.py`
- Modify: `squirrel-backend/services/subscription_video_service.py`
- Modify: `squirrel-backend/core/extraction/services/video_persistence.py`

**Step 1: Implement service helpers**

- Backfill one user's subscription feed rows
- Delete one user's subscription feed rows
- Update NSFW rows for one user/subscription
- Fan out one `(subscription_id, video_id)` link to active users
- Refresh denormalized video metadata for one `video_id`

**Step 2: Wire write paths**

- Call backfill on create/restore subscription
- Call delete on unsubscribe
- Call NSFW update on toggle
- Call fan-out on new subscription-video link
- Call metadata refresh when video fields change

### Task 4: Rewrite `list_videos` to read from the feed table

**Files:**
- Modify: `squirrel-backend/services/video_service.py`

**Step 1: Replace the current list query**

- Read candidate rows from `user_video_feed`
- Collapse current page to unique `video_id`s
- Compute `withTotal` from the feed candidate subquery

**Step 2: Replace heavy loaders with current-page detail queries**

- Load base video rows for the page ids
- Load current-user histories for the page ids
- Load current-user subscription rows for the page ids from `user_video_feed + subscription`
- Load creators for page ids only

### Task 5: Verify and finish

**Files:**
- No new files beyond the above

**Step 1: Run targeted tests**

```bash
cd squirrel-backend
pytest tests/services/test_video_service.py tests/services/test_subscription_service.py -q
```

**Step 2: Run broader backend verification**

```bash
cd squirrel-backend
pytest tests/services -q
```

**Step 3: Confirm no API shape regression**

- Re-read `routes/video.py`
- Confirm `/api/video/list` response keys remain `total`, `page`, `pageSize`, `data`

