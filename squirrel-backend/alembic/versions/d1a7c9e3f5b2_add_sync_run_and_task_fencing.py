"""add durable subscription sync runs and task fencing

Revision ID: d1a7c9e3f5b2
Revises: c7e4a2b9d5f1
Create Date: 2026-07-19

Deployment contract
-------------------
This revision is intentionally a stop-the-world upgrade. Stop API writers,
schedulers, and crawl workers, then take a database backup before running it.
It acquires ACCESS EXCLUSIVE locks with a short lock timeout so an accidentally
live deployment fails instead of waiting indefinitely. Old application binaries
must not be restarted after the revision is committed: they do not populate the
run ledger or lease-fencing columns.

The duplicate-subscription merge is data-destructive on downgrade: schema
changes can be reverted, but rows merged into their canonical subscription are
not recreated. Historical ``subscription_video`` rows missing either parent
are unambiguous junction-table garbage, so they are removed with an operator-
visible warning before foreign keys are added. In-flight work owned by duplicate
subscriptions cannot remain valid after those subscriptions and sync states are
merged, so it is cancelled with audit fields intact and made immediately
reschedulable on the canonical subscription. Other unsafe or ambiguous source
data is rejected explicitly rather than being silently discarded.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd1a7c9e3f5b2'
down_revision: str | None = 'c7e4a2b9d5f1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Python's str.strip() whitespace set. Keeping this explicit makes PostgreSQL
# backfill keys identical to build_subscription_canonical_key().
_PYTHON_STRIP_CHARS = (
    r"U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020"
    r"\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006"
    r"\2007\2008\2009\200A\2028\2029\202F\205F\3000'"
)
_NORMALIZED_URL = f'btrim(s.url, {_PYTHON_STRIP_CHARS})'


def _lock_legacy_tables() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        """
        LOCK TABLE
            subscription,
            user_subscription,
            subscription_video,
            video,
            subscription_sync_state,
            crawl_job,
            crawl_task
        IN ACCESS EXCLUSIVE MODE
        """,
    )


def _remove_orphan_subscription_video_links() -> None:
    """Discard legacy junction rows that cannot represent a relationship."""
    op.execute(
        """
        DO $$
        DECLARE
            missing_subscription_count bigint;
            missing_video_count bigint;
            missing_both_count bigint;
            removed_count bigint;
        BEGIN
            SELECT
                count(*) FILTER (WHERE s.id IS NULL AND v.id IS NOT NULL),
                count(*) FILTER (WHERE s.id IS NOT NULL AND v.id IS NULL),
                count(*) FILTER (WHERE s.id IS NULL AND v.id IS NULL)
            INTO
                missing_subscription_count,
                missing_video_count,
                missing_both_count
            FROM subscription_video sv
            LEFT JOIN subscription s ON s.id = sv.subscription_id
            LEFT JOIN video v ON v.id = sv.video_id
            WHERE s.id IS NULL OR v.id IS NULL;

            DELETE FROM subscription_video sv
            WHERE NOT EXISTS (
                SELECT 1 FROM subscription s WHERE s.id = sv.subscription_id
            ) OR NOT EXISTS (
                SELECT 1 FROM video v WHERE v.id = sv.video_id
            );
            GET DIAGNOSTICS removed_count = ROW_COUNT;

            IF removed_count > 0 THEN
                RAISE WARNING USING MESSAGE = format(
                    'd1a7c9e3f5b2: removed %s orphan subscription_video rows '
                    '(missing subscription=%s, missing video=%s, missing both=%s)',
                    removed_count,
                    missing_subscription_count,
                    missing_video_count,
                    missing_both_count
                );
            END IF;
        END
        $$
        """,
    )


def _assert_existing_references_are_valid() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM subscription_video sv
                LEFT JOIN subscription s ON s.id = sv.subscription_id
                WHERE s.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: subscription_video contains orphan subscription_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM subscription_video sv
                LEFT JOIN video v ON v.id = sv.video_id
                WHERE v.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: subscription_video contains orphan video_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM subscription_sync_state ss
                LEFT JOIN subscription s ON s.id = ss.subscription_id
                WHERE s.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: subscription_sync_state contains orphan subscription_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_job cj
                LEFT JOIN subscription s ON s.id = cj.subscription_id
                WHERE cj.subscription_id IS NOT NULL AND s.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_job contains orphan subscription_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                LEFT JOIN subscription s ON s.id = ct.subscription_id
                WHERE ct.subscription_id IS NOT NULL AND s.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task contains orphan subscription_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                LEFT JOIN subscription_sync_state ss ON ss.id = ct.sync_state_id
                WHERE ct.sync_state_id IS NOT NULL AND ss.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task contains orphan sync_state_id values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                LEFT JOIN video v ON v.id = ct.video_id
                WHERE ct.video_id IS NOT NULL AND v.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task contains orphan video_id values';
            END IF;
        END
        $$
        """,
    )


def _create_subscription_merge_map() -> None:
    op.execute(
        f"""
        CREATE TEMPORARY TABLE _subscription_merge_member
        ON COMMIT DROP
        AS
        WITH ranked AS (
            SELECT
                s.id AS old_subscription_id,
                {_NORMALIZED_URL} AS normalized_url,
                first_value(s.id) OVER (
                    PARTITION BY {_NORMALIZED_URL}
                    ORDER BY
                        s.is_deleted ASC,
                        s.created_at ASC NULLS LAST,
                        s.id ASC
                ) AS canonical_subscription_id,
                count(*) OVER (PARTITION BY {_NORMALIZED_URL}) AS member_count
            FROM subscription s
            WHERE s.url IS NOT NULL
        )
        SELECT old_subscription_id, canonical_subscription_id, normalized_url
        FROM ranked
        WHERE member_count > 1
        """,
    )
    op.execute(
        """
        ALTER TABLE _subscription_merge_member
        ADD PRIMARY KEY (old_subscription_id)
        """,
    )
    op.execute(
        """
        CREATE INDEX ix_subscription_merge_member_canonical
        ON _subscription_merge_member (canonical_subscription_id)
        """,
    )


def _cancel_duplicate_subscription_work() -> None:
    """Fence legacy work that cannot safely survive a many-to-one merge."""
    op.execute(
        """
        CREATE TEMPORARY TABLE _subscription_merge_job
        ON COMMIT DROP
        AS
        SELECT DISTINCT candidate.job_id
        FROM (
            SELECT cj.id AS job_id
            FROM crawl_job cj
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = cj.subscription_id
            WHERE cj.status IN ('pending', 'running')

            UNION ALL

            SELECT ct.job_id
            FROM crawl_task ct
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = ct.subscription_id
            WHERE ct.status IN ('pending', 'retry_wait', 'leased', 'running')
        ) candidate
        """,
    )
    op.execute(
        """
        ALTER TABLE _subscription_merge_job
        ADD PRIMARY KEY (job_id)
        """,
    )
    op.execute(
        """
        CREATE TEMPORARY TABLE _subscription_merge_reschedule
        ON COMMIT DROP
        AS
        SELECT DISTINCT candidate.canonical_subscription_id
        FROM (
            SELECT sm.canonical_subscription_id
            FROM subscription_sync_state ss
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = ss.subscription_id
            WHERE ss.sync_status IN ('queued', 'running')
               OR ss.pending_video_count <> 0
               OR ss.queue_token IS NOT NULL

            UNION ALL

            SELECT sm.canonical_subscription_id
            FROM crawl_job cj
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = cj.subscription_id
            WHERE cj.status IN ('pending', 'running')

            UNION ALL

            SELECT sm.canonical_subscription_id
            FROM crawl_task ct
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = ct.subscription_id
            WHERE ct.status IN ('pending', 'retry_wait', 'leased', 'running')
        ) candidate
        """,
    )
    op.execute(
        """
        ALTER TABLE _subscription_merge_reschedule
        ADD PRIMARY KEY (canonical_subscription_id)
        """,
    )
    op.execute(
        """
        DO $$
        DECLARE
            cancelled_at timestamp := transaction_timestamp();
            cancelled_task_count bigint;
            reconciled_job_count bigint;
            reset_state_count bigint;
        BEGIN
            UPDATE crawl_task ct
            SET
                status = 'cancelled',
                dedupe_key = NULL,
                lease_until = NULL,
                worker_id = NULL,
                last_error = 'cancelled_for_subscription_merge',
                last_error_type = 'cancelled',
                updated_at = cancelled_at,
                finished_at = cancelled_at
            WHERE ct.status IN ('pending', 'retry_wait', 'leased', 'running')
              AND (
                  EXISTS (
                      SELECT 1
                      FROM _subscription_merge_member sm
                      WHERE sm.old_subscription_id = ct.subscription_id
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM crawl_job cj
                      JOIN _subscription_merge_member sm
                        ON sm.old_subscription_id = cj.subscription_id
                      WHERE cj.id = ct.job_id
                        AND (
                            ct.subscription_id IS NULL
                            OR ct.subscription_id = cj.subscription_id
                        )
                  )
              );
            GET DIAGNOSTICS cancelled_task_count = ROW_COUNT;

            UPDATE subscription_sync_state ss
            SET
                sync_status = 'idle',
                queue_token = NULL,
                queued_at = NULL,
                locked_at = NULL,
                pending_video_count = 0,
                next_sync_at = cancelled_at,
                last_error = 'cancelled_for_subscription_merge',
                version = ss.version + 1,
                updated_at = cancelled_at
            FROM _subscription_merge_member sm
            JOIN _subscription_merge_reschedule scope
              ON scope.canonical_subscription_id = sm.canonical_subscription_id
            WHERE ss.subscription_id = sm.old_subscription_id;
            GET DIAGNOSTICS reset_state_count = ROW_COUNT;

            WITH task_summary AS (
                SELECT
                    mj.job_id,
                    count(ct.id) AS task_count,
                    count(ct.id) FILTER (
                        WHERE ct.status IN ('pending', 'retry_wait', 'leased', 'running')
                    ) AS active_count,
                    count(ct.id) FILTER (
                        WHERE ct.status IN ('retry_wait', 'leased', 'running')
                           OR ct.started_at IS NOT NULL
                    ) AS started_count,
                    count(ct.id) FILTER (WHERE ct.status = 'succeeded') AS succeeded_count,
                    count(ct.id) FILTER (WHERE ct.status = 'dead') AS dead_count,
                    count(ct.id) FILTER (WHERE ct.status = 'cancelled') AS cancelled_count
                FROM _subscription_merge_job mj
                LEFT JOIN crawl_task ct ON ct.job_id = mj.job_id
                GROUP BY mj.job_id
            )
            UPDATE crawl_job cj
            SET
                status = CASE
                    WHEN summary.active_count > 0 AND summary.started_count > 0
                    THEN 'running'
                    WHEN summary.active_count > 0
                    THEN 'pending'
                    WHEN summary.task_count = 0
                      OR summary.cancelled_count = summary.task_count
                    THEN 'cancelled'
                    WHEN summary.dead_count = summary.task_count
                    THEN 'failed'
                    WHEN summary.dead_count > 0 OR summary.cancelled_count > 0
                    THEN 'partial_failed'
                    WHEN summary.succeeded_count = summary.task_count
                    THEN 'succeeded'
                    ELSE 'cancelled'
                END,
                error_message = CASE
                    WHEN summary.active_count > 0
                    THEN NULL
                    WHEN summary.task_count = 0
                      OR summary.cancelled_count = summary.task_count
                    THEN 'cancelled_for_subscription_merge'
                    WHEN summary.dead_count = summary.task_count
                    THEN 'job_failed'
                    WHEN summary.dead_count > 0 OR summary.cancelled_count > 0
                    THEN 'partial_failed'
                    WHEN summary.succeeded_count = summary.task_count
                    THEN NULL
                    ELSE 'cancelled_for_subscription_merge'
                END,
                updated_at = cancelled_at,
                finished_at = CASE
                    WHEN summary.active_count > 0 THEN NULL
                    ELSE cancelled_at
                END
            FROM task_summary summary
            WHERE cj.id = summary.job_id;
            GET DIAGNOSTICS reconciled_job_count = ROW_COUNT;

            IF cancelled_task_count > 0 OR reconciled_job_count > 0 OR reset_state_count > 0 THEN
                RAISE WARNING USING MESSAGE = format(
                    'd1a7c9e3f5b2: cancelled duplicate-subscription work '
                    '(tasks=%s, reconciled jobs=%s, reset sync states=%s); '
                    'canonical states are due for rescheduling',
                    cancelled_task_count,
                    reconciled_job_count,
                    reset_state_count
                );
            END IF;
        END
        $$
        """,
    )


def _assert_subscription_merge_is_safe() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM subscription s
                JOIN _subscription_merge_member sm
                  ON sm.old_subscription_id = s.id
                GROUP BY sm.canonical_subscription_id
                HAVING count(DISTINCT s.type) > 1
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: duplicate subscription URLs have conflicting content types';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                JOIN _subscription_merge_member sm
                  ON sm.old_subscription_id = ct.subscription_id
                WHERE ct.status IN ('pending', 'retry_wait', 'leased', 'running')
            ) OR EXISTS (
                SELECT 1
                FROM crawl_job cj
                JOIN _subscription_merge_member sm
                  ON sm.old_subscription_id = cj.subscription_id
                WHERE cj.status IN ('pending', 'running')
            ) OR EXISTS (
                SELECT 1
                FROM subscription_sync_state ss
                JOIN _subscription_merge_member sm
                  ON sm.old_subscription_id = ss.subscription_id
                WHERE ss.sync_status IN ('queued', 'running')
                   OR ss.pending_video_count <> 0
                   OR ss.queue_token IS NOT NULL
            ) THEN
                RAISE EXCEPTION USING
                    MESSAGE = 'd1a7c9e3f5b2: duplicate subscription work remains active after cancellation',
                    HINT = 'Inspect task, job, and sync-state status values before retrying the stopped upgrade.';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM subscription_sync_state ss
                JOIN _subscription_merge_member sm
                  ON sm.old_subscription_id = ss.subscription_id
                WHERE ss.site IS NOT NULL
                GROUP BY sm.canonical_subscription_id, ss.sync_mode
                HAVING count(DISTINCT ss.site) > 1
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: duplicate subscription sync states disagree on site';
            END IF;
        END
        $$
        """,
    )


def _merge_user_subscriptions() -> None:
    op.execute(
        """
        CREATE TEMPORARY TABLE _user_subscription_merge
        ON COMMIT DROP
        AS
        SELECT
            us.user_id,
            sm.canonical_subscription_id,
            (
                array_agg(
                    us.id
                    ORDER BY
                        (us.subscription_id = sm.canonical_subscription_id) DESC,
                        us.id ASC
                )
            )[1] AS keeper_id,
            bool_and(us.is_deleted) AS is_deleted,
            bool_or(us.is_nsfw) AS is_nsfw,
            bool_or(us.is_special_followed) AS is_special_followed,
            max(us.intent_version) + 1 AS intent_version,
            min(us.created_at) AS created_at,
            max(us.updated_at) AS updated_at
        FROM user_subscription us
        JOIN _subscription_merge_member sm
          ON sm.old_subscription_id = us.subscription_id
        GROUP BY us.user_id, sm.canonical_subscription_id
        """,
    )

    op.execute(
        """
        DELETE FROM user_subscription us
        USING _subscription_merge_member sm, _user_subscription_merge um
        WHERE sm.old_subscription_id = us.subscription_id
          AND um.user_id = us.user_id
          AND um.canonical_subscription_id = sm.canonical_subscription_id
          AND us.id <> um.keeper_id
        """,
    )
    op.execute(
        """
        UPDATE user_subscription us
        SET
            subscription_id = um.canonical_subscription_id,
            is_deleted = um.is_deleted,
            is_nsfw = um.is_nsfw,
            is_special_followed = um.is_special_followed,
            intent_version = um.intent_version,
            created_at = um.created_at,
            updated_at = um.updated_at
        FROM _user_subscription_merge um
        WHERE us.id = um.keeper_id
        """,
    )


def _merge_subscription_videos() -> None:
    op.execute(
        """
        INSERT INTO subscription_video (subscription_id, video_id, created_at)
        SELECT
            sm.canonical_subscription_id,
            sv.video_id,
            min(sv.created_at)
        FROM subscription_video sv
        JOIN _subscription_merge_member sm
          ON sm.old_subscription_id = sv.subscription_id
        GROUP BY sm.canonical_subscription_id, sv.video_id
        ON CONFLICT (subscription_id, video_id)
        DO UPDATE SET created_at = LEAST(subscription_video.created_at, EXCLUDED.created_at)
        """,
    )
    op.execute(
        """
        DELETE FROM subscription_video sv
        USING _subscription_merge_member sm
        WHERE sv.subscription_id = sm.old_subscription_id
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )


def _merge_sync_states() -> None:
    op.execute(
        """
        CREATE TEMPORARY TABLE _subscription_sync_state_merge
        ON COMMIT DROP
        AS
        WITH ranked AS (
            SELECT
                ss.id AS old_sync_state_id,
                sm.canonical_subscription_id,
                first_value(ss.id) OVER (
                    PARTITION BY sm.canonical_subscription_id, ss.sync_mode
                    ORDER BY
                        ss.last_success_at DESC NULLS LAST,
                        ss.last_sync_at DESC NULLS LAST,
                        ss.updated_at DESC NULLS LAST,
                        ss.id DESC
                ) AS keeper_sync_state_id
            FROM subscription_sync_state ss
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = ss.subscription_id
        )
        SELECT old_sync_state_id, canonical_subscription_id, keeper_sync_state_id
        FROM ranked
        """,
    )
    op.execute(
        """
        ALTER TABLE _subscription_sync_state_merge
        ADD PRIMARY KEY (old_sync_state_id)
        """,
    )

    op.execute(
        """
        UPDATE crawl_task ct
        SET
            sync_state_id = ssm.keeper_sync_state_id,
            payload = CASE
                WHEN jsonb_typeof(ct.payload::jsonb) = 'object'
                 AND ct.payload::jsonb ? 'sync_state_id'
                THEN jsonb_set(
                    ct.payload::jsonb,
                    '{sync_state_id}',
                    to_jsonb(ssm.keeper_sync_state_id),
                    false
                )::json
                ELSE ct.payload
            END
        FROM _subscription_sync_state_merge ssm
        WHERE ct.sync_state_id = ssm.old_sync_state_id
          AND ssm.old_sync_state_id <> ssm.keeper_sync_state_id
        """,
    )
    op.execute(
        """
        UPDATE crawl_task ct
        SET payload = jsonb_set(
            ct.payload::jsonb,
            '{sync_state_id}',
            to_jsonb(ssm.keeper_sync_state_id),
            false
        )::json
        FROM _subscription_sync_state_merge ssm
        WHERE jsonb_typeof(ct.payload::jsonb) = 'object'
          AND ct.payload ->> 'sync_state_id' = ssm.old_sync_state_id::text
          AND ssm.old_sync_state_id <> ssm.keeper_sync_state_id
        """,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM _subscription_sync_state_merge ssm
                JOIN crawl_task ct
                  ON ct.sync_state_id = ssm.old_sync_state_id
                  OR (
                      jsonb_typeof(ct.payload::jsonb) = 'object'
                      AND ct.payload ->> 'sync_state_id' = ssm.old_sync_state_id::text
                  )
                WHERE ssm.old_sync_state_id <> ssm.keeper_sync_state_id
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: a duplicate sync state still has task references after merge';
            END IF;
        END
        $$
        """,
    )
    op.execute(
        """
        DELETE FROM subscription_sync_state ss
        USING _subscription_sync_state_merge ssm
        WHERE ss.id = ssm.old_sync_state_id
          AND ssm.old_sync_state_id <> ssm.keeper_sync_state_id
        """,
    )
    op.execute(
        """
        UPDATE subscription_sync_state ss
        SET subscription_id = keepers.canonical_subscription_id
        FROM (
            SELECT DISTINCT keeper_sync_state_id, canonical_subscription_id
            FROM _subscription_sync_state_merge
        ) keepers
        WHERE ss.id = keepers.keeper_sync_state_id
        """,
    )


def _rewrite_subscription_references() -> None:
    op.execute(
        """
        UPDATE crawl_job cj
        SET
            subscription_id = sm.canonical_subscription_id,
            payload = CASE
                WHEN cj.payload IS NOT NULL
                 AND jsonb_typeof(cj.payload::jsonb) = 'object'
                 AND cj.payload::jsonb ? 'subscription_id'
                THEN jsonb_set(
                    cj.payload::jsonb,
                    '{subscription_id}',
                    to_jsonb(sm.canonical_subscription_id),
                    false
                )::json
                ELSE cj.payload
            END
        FROM _subscription_merge_member sm
        WHERE cj.subscription_id = sm.old_subscription_id
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )
    op.execute(
        """
        UPDATE crawl_job cj
        SET payload = jsonb_set(
            cj.payload::jsonb,
            '{subscription_id}',
            to_jsonb(sm.canonical_subscription_id),
            false
        )::json
        FROM _subscription_merge_member sm
        WHERE cj.payload IS NOT NULL
          AND jsonb_typeof(cj.payload::jsonb) = 'object'
          AND cj.payload ->> 'subscription_id' = sm.old_subscription_id::text
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )
    op.execute(
        """
        UPDATE crawl_task ct
        SET
            subscription_id = sm.canonical_subscription_id,
            payload = CASE
                WHEN jsonb_typeof(ct.payload::jsonb) = 'object'
                 AND ct.payload::jsonb ? 'subscription_id'
                THEN jsonb_set(
                    ct.payload::jsonb,
                    '{subscription_id}',
                    to_jsonb(sm.canonical_subscription_id),
                    false
                )::json
                ELSE ct.payload
            END
        FROM _subscription_merge_member sm
        WHERE ct.subscription_id = sm.old_subscription_id
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )
    op.execute(
        """
        UPDATE crawl_task ct
        SET payload = jsonb_set(
            ct.payload::jsonb,
            '{subscription_id}',
            to_jsonb(sm.canonical_subscription_id),
            false
        )::json
        FROM _subscription_merge_member sm
        WHERE jsonb_typeof(ct.payload::jsonb) = 'object'
          AND ct.payload ->> 'subscription_id' = sm.old_subscription_id::text
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )

    # Old tasks occasionally carried only a state id. Fill the redundant
    # subscription column before enforcing both foreign keys.
    op.execute(
        """
        UPDATE crawl_task ct
        SET subscription_id = ss.subscription_id
        FROM subscription_sync_state ss
        WHERE ct.sync_state_id = ss.id
          AND ct.subscription_id IS NULL
        """,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                JOIN subscription_sync_state ss ON ss.id = ct.sync_state_id
                WHERE ct.subscription_id IS DISTINCT FROM ss.subscription_id
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task subscription_id conflicts with sync_state_id';
            END IF;
        END
        $$
        """,
    )


def _merge_subscription_rows() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                WITH removed_subscription AS (
                    SELECT old_subscription_id
                    FROM _subscription_merge_member
                    WHERE old_subscription_id <> canonical_subscription_id
                )
                SELECT 1
                FROM user_subscription us
                JOIN removed_subscription rs
                  ON rs.old_subscription_id = us.subscription_id

                UNION ALL

                SELECT 1
                FROM subscription_video sv
                JOIN removed_subscription rs
                  ON rs.old_subscription_id = sv.subscription_id

                UNION ALL

                SELECT 1
                FROM subscription_sync_state ss
                JOIN removed_subscription rs
                  ON rs.old_subscription_id = ss.subscription_id

                UNION ALL

                SELECT 1
                FROM crawl_job cj
                JOIN removed_subscription rs
                  ON rs.old_subscription_id = cj.subscription_id

                UNION ALL

                SELECT 1
                FROM crawl_job cj
                JOIN removed_subscription rs
                  ON cj.payload IS NOT NULL
                 AND jsonb_typeof(cj.payload::jsonb) = 'object'
                 AND cj.payload ->> 'subscription_id' = rs.old_subscription_id::text

                UNION ALL

                SELECT 1
                FROM crawl_task ct
                JOIN removed_subscription rs
                  ON rs.old_subscription_id = ct.subscription_id

                UNION ALL

                SELECT 1
                FROM crawl_task ct
                JOIN removed_subscription rs
                  ON jsonb_typeof(ct.payload::jsonb) = 'object'
                 AND ct.payload ->> 'subscription_id' = rs.old_subscription_id::text
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: a duplicate subscription still has references after merge';
            END IF;
        END
        $$
        """,
    )
    op.execute(
        """
        WITH merged AS (
            SELECT
                sm.canonical_subscription_id,
                min(sm.normalized_url) AS normalized_url,
                max(s.total_videos) AS total_videos,
                bool_and(s.is_deleted) AS is_deleted,
                min(s.created_at) AS created_at,
                max(s.updated_at) AS updated_at,
                (array_agg(s.name ORDER BY s.updated_at DESC NULLS LAST, s.id DESC))[1] AS name,
                (
                    array_agg(s.avatar ORDER BY s.updated_at DESC NULLS LAST, s.id DESC)
                    FILTER (WHERE s.avatar IS NOT NULL)
                )[1] AS avatar,
                (
                    array_agg(s.description ORDER BY s.updated_at DESC NULLS LAST, s.id DESC)
                    FILTER (WHERE s.description IS NOT NULL)
                )[1] AS description,
                (
                    jsonb_agg(s.extra_data::jsonb ORDER BY s.updated_at DESC NULLS LAST, s.id DESC)
                    FILTER (WHERE s.extra_data IS NOT NULL)
                )->0 AS extra_data
            FROM subscription s
            JOIN _subscription_merge_member sm
              ON sm.old_subscription_id = s.id
            GROUP BY sm.canonical_subscription_id
        )
        UPDATE subscription s
        SET
            url = merged.normalized_url,
            name = merged.name,
            avatar = merged.avatar,
            description = merged.description,
            total_videos = merged.total_videos,
            is_deleted = CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM user_subscription us
                    WHERE us.subscription_id = merged.canonical_subscription_id
                      AND us.is_deleted IS FALSE
                ) THEN FALSE
                ELSE merged.is_deleted
            END,
            extra_data = merged.extra_data::json,
            created_at = merged.created_at,
            updated_at = merged.updated_at
        FROM merged
        WHERE s.id = merged.canonical_subscription_id
        """,
    )
    op.execute(
        """
        DELETE FROM subscription s
        USING _subscription_merge_member sm
        WHERE s.id = sm.old_subscription_id
          AND sm.old_subscription_id <> sm.canonical_subscription_id
        """,
    )


def _backfill_canonical_keys() -> None:
    normalized_url = f'btrim(url, {_PYTHON_STRIP_CHARS})'
    op.execute(
        f"""
        UPDATE subscription
        SET canonical_key = encode(
            sha256(convert_to({normalized_url}, 'UTF8')),
            'hex'
        )
        WHERE url IS NOT NULL
        """,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT canonical_key
                FROM subscription
                WHERE canonical_key IS NOT NULL
                GROUP BY canonical_key
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: canonical subscription key collision remains after merge';
            END IF;
        END
        $$
        """,
    )
    op.create_check_constraint(
        'ck_subscription_url_canonical_key_presence',
        'subscription',
        '(url IS NULL AND canonical_key IS NULL) OR (url IS NOT NULL AND canonical_key IS NOT NULL)',
    )
    op.create_index('uix_subscription_canonical_key', 'subscription', ['canonical_key'], unique=True)


def _create_canonical_key_trigger() -> None:
    normalized_url = f'btrim(NEW.url, {_PYTHON_STRIP_CHARS})'
    op.execute(
        f"""
        CREATE FUNCTION d1_sync_subscription_canonical_key()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.canonical_key := CASE
                WHEN NEW.url IS NULL THEN NULL
                ELSE encode(
                    sha256(convert_to({normalized_url}, 'UTF8')),
                    'hex'
                )
            END;
            RETURN NEW;
        END
        $$
        """,
    )
    op.execute(
        """
        CREATE TRIGGER trg_subscription_canonical_key
        BEFORE INSERT OR UPDATE OF url, canonical_key
        ON subscription
        FOR EACH ROW
        EXECUTE FUNCTION d1_sync_subscription_canonical_key()
        """,
    )


def _create_sync_run_table() -> None:
    op.create_table(
        'subscription_sync_run',
        sa.Column('id', sa.VARCHAR(length=64), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('sync_state_id', sa.Integer(), nullable=True),
        sa.Column('site', sa.VARCHAR(length=64), nullable=False, server_default=''),
        sa.Column('sync_mode', sa.VARCHAR(length=16), nullable=False),
        sa.Column('trigger', sa.VARCHAR(length=32), nullable=True),
        sa.Column('status', sa.VARCHAR(length=24), nullable=False, server_default='queued'),
        sa.Column('queue_token', sa.VARCHAR(length=64), nullable=True),
        sa.Column('request_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('trace_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('cursor_in', sa.JSON(), nullable=True),
        sa.Column('cursor_out', sa.JSON(), nullable=True),
        sa.Column('videos_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_enqueued', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.TEXT(), nullable=True),
        sa.Column('last_error_type', sa.VARCHAR(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ['subscription_id'],
            ['subscription.id'],
            name='fk_subscription_sync_run_subscription_id_subscription',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['sync_state_id'],
            ['subscription_sync_state.id'],
            name='fk_subscription_sync_run_sync_state_id_sync_state',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscription_sync_run_state_status', 'subscription_sync_run', ['sync_state_id', 'status'])
    op.create_index(
        'ix_subscription_sync_run_subscription_created',
        'subscription_sync_run',
        ['subscription_id', 'created_at'],
    )
    op.create_index('ix_subscription_sync_run_status_updated', 'subscription_sync_run', ['status', 'updated_at'])
    op.create_index('ix_subscription_sync_run_trace_id', 'subscription_sync_run', ['trace_id'])


def _backfill_sync_runs() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM crawl_task
                WHERE payload ->> 'run_id' IS NOT NULL
                  AND length(payload ->> 'run_id') > 64
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task payload contains a run_id longer than 64 characters';
            END IF;
        END
        $$
        """,
    )
    op.execute(
        """
        UPDATE crawl_task
        SET run_id = NULLIF(payload ->> 'run_id', '')
        WHERE payload ->> 'run_id' IS NOT NULL
        """,
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                LEFT JOIN subscription_sync_state ss ON ss.id = ct.sync_state_id
                LEFT JOIN subscription s ON s.id = COALESCE(ct.subscription_id, ss.subscription_id)
                WHERE ct.run_id IS NOT NULL
                  AND s.id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: run-bound crawl_task cannot be associated with a subscription';
            END IF;

            IF EXISTS (
                SELECT ct.run_id
                FROM crawl_task ct
                LEFT JOIN subscription_sync_state ss ON ss.id = ct.sync_state_id
                WHERE ct.run_id IS NOT NULL
                GROUP BY ct.run_id
                HAVING count(DISTINCT COALESCE(ct.subscription_id, ss.subscription_id)) > 1
                    OR count(DISTINCT ct.sync_state_id) > 1
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: one run_id points at multiple subscriptions or sync states';
            END IF;
        END
        $$
        """,
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                ct.*,
                COALESCE(ct.subscription_id, ss.subscription_id) AS resolved_subscription_id,
                row_number() OVER (
                    PARTITION BY ct.run_id
                    ORDER BY
                        (ct.task_type LIKE 'subscription_sync%') DESC,
                        ct.created_at DESC,
                        ct.id DESC
                ) AS representative_rank,
                bool_or(ct.status IN ('leased', 'running')) OVER (PARTITION BY ct.run_id) AS has_running,
                bool_or(ct.status IN ('pending', 'retry_wait')) OVER (PARTITION BY ct.run_id) AS has_queued,
                bool_or(ct.status = 'dead') OVER (PARTITION BY ct.run_id) AS has_dead,
                bool_or(ct.status = 'cancelled') OVER (PARTITION BY ct.run_id) AS has_cancelled,
                min(ct.created_at) OVER (PARTITION BY ct.run_id) AS run_created_at,
                max(ct.updated_at) OVER (PARTITION BY ct.run_id) AS run_updated_at,
                min(ct.started_at) OVER (PARTITION BY ct.run_id) AS run_started_at,
                max(ct.finished_at) OVER (PARTITION BY ct.run_id) AS run_finished_at
            FROM crawl_task ct
            LEFT JOIN subscription_sync_state ss ON ss.id = ct.sync_state_id
            WHERE ct.run_id IS NOT NULL
        )
        INSERT INTO subscription_sync_run (
            id,
            subscription_id,
            sync_state_id,
            site,
            sync_mode,
            trigger,
            status,
            queue_token,
            request_id,
            trace_id,
            cursor_in,
            created_at,
            updated_at,
            started_at,
            finished_at,
            last_error,
            last_error_type
        )
        SELECT
            ranked.run_id,
            ranked.resolved_subscription_id,
            ranked.sync_state_id,
            ranked.site,
            COALESCE(ranked.payload ->> 'mode', ss.sync_mode, 'incremental'),
            ranked.payload ->> 'trigger',
            CASE
                WHEN ranked.has_running THEN 'running'
                WHEN ranked.has_queued THEN 'queued'
                WHEN ranked.has_dead THEN 'failed'
                WHEN ranked.has_cancelled THEN 'cancelled'
                ELSE 'succeeded'
            END,
            ranked.payload ->> 'queue_token',
            ranked.payload ->> 'request_id',
            ranked.trace_id,
            ss.cursor_payload,
            ranked.run_created_at,
            ranked.run_updated_at,
            ranked.run_started_at,
            CASE
                WHEN ranked.has_running OR ranked.has_queued THEN NULL
                ELSE ranked.run_finished_at
            END,
            CASE WHEN ranked.has_dead THEN ranked.last_error ELSE NULL END,
            CASE WHEN ranked.has_dead THEN ranked.last_error_type ELSE NULL END
        FROM ranked
        LEFT JOIN subscription_sync_state ss ON ss.id = ranked.sync_state_id
        WHERE ranked.representative_rank = 1
        """,
    )
    op.execute(
        """
        UPDATE subscription_sync_state ss
        SET current_run_id = active.run_id
        FROM (
            SELECT DISTINCT ON (sync_state_id) sync_state_id, run_id
            FROM crawl_task
            WHERE sync_state_id IS NOT NULL
              AND run_id IS NOT NULL
              AND status IN ('pending', 'retry_wait', 'leased', 'running')
            ORDER BY sync_state_id, created_at DESC, id DESC
        ) active
        WHERE ss.id = active.sync_state_id
        """,
    )


def _assert_run_references_are_consistent() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM subscription_sync_run sr
                JOIN subscription_sync_state ss ON ss.id = sr.sync_state_id
                WHERE sr.subscription_id <> ss.subscription_id
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: sync run subscription_id conflicts with sync_state_id';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM subscription_sync_state ss
                JOIN subscription_sync_run sr ON sr.id = ss.current_run_id
                WHERE ss.id <> sr.sync_state_id
                   OR ss.subscription_id <> sr.subscription_id
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: current_run_id does not belong to its sync state';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM crawl_task ct
                JOIN subscription_sync_run sr ON sr.id = ct.run_id
                WHERE ct.subscription_id IS DISTINCT FROM sr.subscription_id
                   OR ct.sync_state_id IS DISTINCT FROM sr.sync_state_id
            ) THEN
                RAISE EXCEPTION
                    'd1a7c9e3f5b2: crawl_task run_id conflicts with its subscription or sync state';
            END IF;
        END
        $$
        """,
    )


def _create_reference_constraints() -> None:
    op.create_foreign_key(
        'fk_subscription_video_subscription_id_subscription',
        'subscription_video',
        'subscription',
        ['subscription_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_subscription_video_video_id_video',
        'subscription_video',
        'video',
        ['video_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_subscription_sync_state_subscription_id_subscription',
        'subscription_sync_state',
        'subscription',
        ['subscription_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'fk_subscription_sync_state_current_run_id_sync_run',
        'subscription_sync_state',
        'subscription_sync_run',
        ['current_run_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_crawl_job_subscription_id_subscription',
        'crawl_job',
        'subscription',
        ['subscription_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_crawl_task_subscription_id_subscription',
        'crawl_task',
        'subscription',
        ['subscription_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_crawl_task_sync_state_id_sync_state',
        'crawl_task',
        'subscription_sync_state',
        ['sync_state_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_crawl_task_run_id_sync_run',
        'crawl_task',
        'subscription_sync_run',
        ['run_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_crawl_task_video_id_video',
        'crawl_task',
        'video',
        ['video_id'],
        ['id'],
        ondelete='SET NULL',
    )


def upgrade() -> None:
    _lock_legacy_tables()
    _remove_orphan_subscription_video_links()
    _assert_existing_references_are_valid()

    op.add_column(
        'user_subscription',
        sa.Column('intent_version', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('subscription', sa.Column('canonical_key', sa.VARCHAR(length=64), nullable=True))

    _create_subscription_merge_map()
    _cancel_duplicate_subscription_work()
    _assert_subscription_merge_is_safe()
    _merge_user_subscriptions()
    _merge_subscription_videos()
    _merge_sync_states()
    _rewrite_subscription_references()
    _merge_subscription_rows()
    _backfill_canonical_keys()
    _create_canonical_key_trigger()

    _create_sync_run_table()
    op.add_column('subscription_sync_state', sa.Column('current_run_id', sa.VARCHAR(length=64), nullable=True))
    op.add_column('subscription_sync_state', sa.Column('execution_token', sa.VARCHAR(length=128), nullable=True))
    op.create_index(
        'ix_subscription_sync_state_current_run_id',
        'subscription_sync_state',
        ['current_run_id'],
        unique=False,
    )
    op.add_column('crawl_task', sa.Column('run_id', sa.VARCHAR(length=64), nullable=True))
    op.add_column('crawl_task', sa.Column('lease_token', sa.VARCHAR(length=64), nullable=True))
    op.add_column('crawl_task', sa.Column('lease_generation', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(
        'ix_crawl_task_run_type_status',
        'crawl_task',
        ['run_id', 'task_type', 'status'],
        unique=False,
    )

    _backfill_sync_runs()
    _assert_run_references_are_consistent()
    _create_reference_constraints()


def downgrade() -> None:
    op.drop_constraint('fk_crawl_task_video_id_video', 'crawl_task', type_='foreignkey')
    op.drop_constraint('fk_crawl_task_run_id_sync_run', 'crawl_task', type_='foreignkey')
    op.drop_constraint('fk_crawl_task_sync_state_id_sync_state', 'crawl_task', type_='foreignkey')
    op.drop_constraint('fk_crawl_task_subscription_id_subscription', 'crawl_task', type_='foreignkey')
    op.drop_constraint('fk_crawl_job_subscription_id_subscription', 'crawl_job', type_='foreignkey')
    op.drop_constraint(
        'fk_subscription_sync_state_current_run_id_sync_run',
        'subscription_sync_state',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_subscription_sync_state_subscription_id_subscription',
        'subscription_sync_state',
        type_='foreignkey',
    )
    op.drop_constraint('fk_subscription_video_video_id_video', 'subscription_video', type_='foreignkey')
    op.drop_constraint(
        'fk_subscription_video_subscription_id_subscription',
        'subscription_video',
        type_='foreignkey',
    )

    op.drop_index('ix_crawl_task_run_type_status', table_name='crawl_task')
    op.drop_column('crawl_task', 'lease_generation')
    op.drop_column('crawl_task', 'lease_token')
    op.drop_column('crawl_task', 'run_id')
    op.drop_index('ix_subscription_sync_state_current_run_id', table_name='subscription_sync_state')
    op.drop_column('subscription_sync_state', 'execution_token')
    op.drop_column('subscription_sync_state', 'current_run_id')
    op.drop_index('ix_subscription_sync_run_trace_id', table_name='subscription_sync_run')
    op.drop_index('ix_subscription_sync_run_status_updated', table_name='subscription_sync_run')
    op.drop_index('ix_subscription_sync_run_subscription_created', table_name='subscription_sync_run')
    op.drop_index('ix_subscription_sync_run_state_status', table_name='subscription_sync_run')
    op.drop_table('subscription_sync_run')
    op.execute('DROP TRIGGER trg_subscription_canonical_key ON subscription')
    op.execute('DROP FUNCTION d1_sync_subscription_canonical_key()')
    op.drop_index('uix_subscription_canonical_key', table_name='subscription')
    op.drop_constraint('ck_subscription_url_canonical_key_presence', 'subscription', type_='check')
    op.drop_column('subscription', 'canonical_key')
    op.drop_column('user_subscription', 'intent_version')
