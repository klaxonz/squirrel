"""add subscription control column

Revision ID: 5e778148978b
Revises: 657baf9bdeb6
Create Date: 2024-12-14 21:26:11.250736

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5e778148978b'
down_revision = '657baf9bdeb6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('subscription', sa.Column('is_enable', sa.Boolean(), nullable=False))
    op.add_column('subscription', sa.Column('is_auto_download', sa.Boolean(), nullable=False))
    op.add_column('subscription', sa.Column('is_download_all', sa.Boolean(), nullable=False))
    op.add_column('subscription', sa.Column('is_extract_all', sa.Boolean(), nullable=False))
    op.drop_column('subscription', 'status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('subscription', sa.Column('status', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False))
    op.drop_column('subscription', 'is_extract_all')
    op.drop_column('subscription', 'is_download_all')
    op.drop_column('subscription', 'is_auto_download')
    op.drop_column('subscription', 'is_enable')
    # ### end Alembic commands ###
