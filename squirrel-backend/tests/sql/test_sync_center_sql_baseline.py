from functools import lru_cache
from pathlib import Path
import sys

from dotenv import dotenv_values
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_ENV_PATH = REPO_ROOT / '.env.dev'


def _build_database_url() -> str:
    if not DEV_ENV_PATH.exists():
        pytest.skip(f'Missing dev environment file: {DEV_ENV_PATH}')

    env_values = dotenv_values(DEV_ENV_PATH)
    host = str(env_values.get('POSTGRES_HOST') or '').strip()
    port = str(env_values.get('POSTGRES_PORT') or '').strip()
    user = str(env_values.get('POSTGRES_USER') or '').strip()
    password = str(env_values.get('POSTGRES_PASSWORD') or '').strip()
    database = str(env_values.get('POSTGRES_DATABASE') or '').strip()

    if not all([host, port, user, password, database]):
        pytest.skip('Incomplete Postgres settings in .env.dev')

    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}'


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    return create_engine(
        _build_database_url(),
        pool_pre_ping=True,
        connect_args={
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
        },
    )


def _flatten_plan_nodes(plan_node: dict) -> list[dict]:
    nodes = [plan_node]
    for child in plan_node.get('Plans', []) or []:
        nodes.extend(_flatten_plan_nodes(child))
    return nodes


def _explain_json(session: Session, sql: str, params: dict) -> dict:
    explain_sql = text(f'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}')
    payload = session.execute(explain_sql, params).scalar_one()
    if isinstance(payload, list):
        return payload[0]
    return payload


def _pick_user_id(session: Session) -> int:
    user_id = session.execute(
        text(
            '''
            SELECT us.user_id
            FROM user_subscription us
            JOIN subscription s ON s.id = us.subscription_id
            WHERE us.is_deleted IS FALSE
              AND s.is_deleted IS FALSE
            GROUP BY us.user_id
            ORDER BY COUNT(*) DESC, us.user_id ASC
            LIMIT 1
            '''
        )
    ).scalar()
    if user_id is None:
        pytest.skip('No active subscriptions found in dev database')
    return int(user_id)


def _query_row_count(session: Session, sql: str, params: dict) -> int:
    wrapped_sql = text(f'SELECT COUNT(*) FROM ({sql}) AS query_under_test')
    return int(session.execute(wrapped_sql, params).scalar_one() or 0)


@pytest.fixture(scope='module')
def dev_session():
    engine = _get_engine()
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture(scope='module')
def dev_user_id(dev_session: Session) -> int:
    return _pick_user_id(dev_session)


def test_feed_projection_query_explain_baseline(dev_session: Session, dev_user_id: int):
    sql = '''
        SELECT
            s.id,
            p.current_status,
            rp.run_id
        FROM subscription s
        JOIN user_subscription us ON us.subscription_id = s.id
        LEFT JOIN subscription_sync_subscription_projection p ON p.subscription_id = s.id
        LEFT JOIN subscription_sync_run_projection rp ON rp.run_id = p.latest_run_id
        WHERE us.user_id = :user_id
          AND us.is_deleted IS FALSE
          AND s.is_deleted IS FALSE
    '''
    plan = _explain_json(dev_session, sql, {'user_id': dev_user_id})
    nodes = _flatten_plan_nodes(plan['Plan'])
    relation_names = {node.get('Relation Name') for node in nodes if node.get('Relation Name')}

    assert 'subscription' in relation_names
    assert 'user_subscription' in relation_names
    assert plan.get('Execution Time') is not None


def test_history_runs_query_explain_baseline(dev_session: Session, dev_user_id: int):
    sql = '''
        SELECT
            rp.run_id
        FROM subscription_sync_run_projection rp
        JOIN subscription s ON s.id = rp.subscription_id
        JOIN user_subscription us ON us.subscription_id = s.id
        WHERE us.user_id = :user_id
          AND us.is_deleted IS FALSE
          AND s.is_deleted IS FALSE
        ORDER BY rp.last_event_at DESC
        LIMIT :page_size
    '''
    params = {'user_id': dev_user_id, 'page_size': 20}
    plan = _explain_json(dev_session, sql, params)
    nodes = _flatten_plan_nodes(plan['Plan'])
    node_types = {node.get('Node Type') for node in nodes}
    row_count = _query_row_count(dev_session, sql, params)

    assert 'Limit' in node_types
    assert row_count <= 20
    assert plan.get('Execution Time') is not None


def test_extraction_center_query_explain_baseline(dev_session: Session, dev_user_id: int):
    sql = '''
        SELECT
            s.id,
            t.id
        FROM subscription s
        JOIN user_subscription us ON us.subscription_id = s.id
        JOIN crawl_task t ON t.subscription_id = s.id
        WHERE us.user_id = :user_id
          AND us.is_deleted IS FALSE
          AND s.is_deleted IS FALSE
          AND t.task_type = 'video_extract'
        ORDER BY t.created_at ASC, t.id ASC
    '''
    extraction_rows = _query_row_count(dev_session, sql, {'user_id': dev_user_id})
    if extraction_rows == 0:
        pytest.skip('No video_extract tasks found for selected dev user')

    plan = _explain_json(dev_session, sql, {'user_id': dev_user_id})
    nodes = _flatten_plan_nodes(plan['Plan'])
    relation_names = {node.get('Relation Name') for node in nodes if node.get('Relation Name')}

    assert 'crawl_task' in relation_names
    assert plan.get('Execution Time') is not None
