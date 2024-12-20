"""Email as signin

Revision ID: 073aa9bc98d2
Revises: 235dba32858b
Create Date: 2023-09-16 12:24:28.367099

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "073aa9bc98d2"
down_revision = "235dba32858b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("email", existing_type=sa.VARCHAR(), nullable=False)
        batch_op.create_unique_constraint(None, ["email"])
        batch_op.drop_column("username")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("username", sa.VARCHAR(), nullable=False))
        batch_op.drop_constraint(None, type_="unique")
        batch_op.alter_column("email", existing_type=sa.VARCHAR(), nullable=True)

    # ### end Alembic commands ###
