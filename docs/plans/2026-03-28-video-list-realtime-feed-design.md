# Video List Realtime Feed Design

**Goal:** Replace the current join-heavy realtime video list query with a maintained realtime user feed table so the default list stays fast without using any cache.

**Architecture**

The current `/api/video/list` query computes visibility at read time by joining `user_subscription`, `subscription_video`, `subscription`, and `video`, then de-duplicating with `DISTINCT`, sorting, paginating, and finally loading related objects. That shape is the root cause of slow list reads.

The replacement introduces a realtime `user_video_feed` projection table. Each row represents one `(user_id, subscription_id, video_id)` visibility edge with the sort/filter fields needed by the list query (`publish_date`, `video_created_at`, `domain`, `is_nsfw`). Read time becomes:

1. Filter and page over `user_video_feed`
2. Collapse to unique `video_id`s for the current page
3. Fetch only current-page video details, current user history, and current user subscriptions

This is not a cache. It is a transactional projection maintained on subscription and video write paths.

**Write Paths**

- New subscription created/restored: backfill `user_video_feed` from existing `subscription_video`
- Subscription removed: delete that user's feed rows for the subscription
- User NSFW toggle: update `is_nsfw` on that user's feed rows for the subscription
- New `subscription_video` link: fan out rows for all active `user_subscription`s on that subscription
- Video metadata change: refresh denormalized sort/filter columns on existing feed rows for that video

**Read Path**

- `/api/video/list` will read candidate rows from `user_video_feed`
- The API response shape stays unchanged
- `withTotal` remains supported
- Search/query behavior can still fall back to additional `video` predicates when needed, but the no-search default path stays feed-first

**Testing**

- Service tests for `video_service.list_videos`
- Service tests for feed maintenance on unsubscribe / NSFW toggle / subscription-video link creation

