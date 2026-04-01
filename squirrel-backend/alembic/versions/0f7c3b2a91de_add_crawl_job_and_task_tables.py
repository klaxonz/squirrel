"""add_crawl_job_and_task_tables

Revision ID: 0f7c3b2a91de
Revises: c4a7d1e2f9b3
Create Date: 2026-04-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0f7c3b2a91de'
down_revision = 'c4a7d1e2f9b3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crawl_job',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_type', sa.VARCHAR(length=32), nullable=False),
        sa.Column('source_type', sa.VARCHAR(length=32), nullable=False),
        sa.Column('site', sa.VARCHAR(length=64), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.VARCHAR(length=16), nullable=False, server_default='pending'),
        sa.Column('priority', sa.VARCHAR(length=16), nullable=False, server_default='normal'),
        sa.Column('trace_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('error_message', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_crawl_job_type_status', 'crawl_job', ['job_type', 'status'], unique=False)
    op.create_index('ix_crawl_job_subscription_id', 'crawl_job', ['subscription_id'], unique=False)
    op.create_index('ix_crawl_job_site_priority', 'crawl_job', ['site', 'priority'], unique=False)
    op.create_index('ix_crawl_job_trace_id', 'crawl_job', ['trace_id'], unique=False)

    op.create_table(
        'crawl_task',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('parent_task_id', sa.Integer(), nullable=True),
        sa.Column('task_type', sa.VARCHAR(length=32), nullable=False),
        sa.Column('site', sa.VARCHAR(length=64), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('video_id', sa.Integer(), nullable=True),
        sa.Column('video_url', sa.VARCHAR(length=2048), nullable=True),
        sa.Column('status', sa.VARCHAR(length=16), nullable=False, server_default='pending'),
        sa.Column('priority', sa.VARCHAR(length=16), nullable=False, server_default='normal'),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('dedupe_key', sa.VARCHAR(length=255), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_run_at', sa.DateTime(), nullable=False),
        sa.Column('lease_until', sa.DateTime(), nullable=True),
        sa.Column('worker_id', sa.VARCHAR(length=128), nullable=True),
        sa.Column('last_error', sa.TEXT(), nullable=True),
        sa.Column('last_error_type', sa.VARCHAR(length=128), nullable=True),
        sa.Column('trace_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['crawl_job.id']),
        sa.ForeignKeyConstraint(['parent_task_id'], ['crawl_task.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedupe_key', name='uq_crawl_task_dedupe_key'),
    )
    op.create_index('ix_crawl_task_runnable_lookup', 'crawl_task', ['status', 'next_run_at', 'priority', 'site'], unique=False)
    op.create_index('ix_crawl_task_lease_until', 'crawl_task', ['lease_until'], unique=False)
    op.create_index('ix_crawl_task_site_status', 'crawl_task', ['site', 'status'], unique=False)
    op.create_index('ix_crawl_task_job_id', 'crawl_task', ['job_id'], unique=False)
    op.create_index('ix_crawl_task_parent_task_id', 'crawl_task', ['parent_task_id'], unique=False)
    op.create_index('ix_crawl_task_type_status', 'crawl_task', ['task_type', 'status'], unique=False)


def downgrade():
    op.drop_index('ix_crawl_task_type_status', table_name='crawl_task')
    op.drop_index('ix_crawl_task_parent_task_id', table_name='crawl_task')
    op.drop_index('ix_crawl_task_job_id', table_name='crawl_task')
    op.drop_index('ix_crawl_task_site_status', table_name='crawl_task')
    op.drop_index('ix_crawl_task_lease_until', table_name='crawl_task')
    op.drop_index('ix_crawl_task_runnable_lookup', table_name='crawl_task')
    op.drop_table('crawl_task')

    op.drop_index('ix_crawl_job_trace_id', table_name='crawl_job')
    op.drop_index('ix_crawl_job_site_priority', table_name='crawl_job')
    op.drop_index('ix_crawl_job_subscription_id', table_name='crawl_job')
    op.drop_index('ix_crawl_job_type_status', table_name='crawl_job')
    op.drop_table('crawl_job')
