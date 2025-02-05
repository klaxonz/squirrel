"""alter video title length

Revision ID: c2776fd2f44a
Revises: 71e7bb6d6875
Create Date: 2025-02-04 19:20:38.530693

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c2776fd2f44a'
down_revision = '71e7bb6d6875'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('video', 'title',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=128),
               type_=sa.VARCHAR(length=512),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('video', 'title',
               existing_type=sa.VARCHAR(length=512),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=128),
               existing_nullable=False)
    # ### end Alembic commands ###
