"""Role System

Revision ID: 0f07a3edd643
Revises: 9b0e597da71c
Create Date: 2023-09-16 12:46:50.000739

"""
import sqlalchemy as sa
import sqlalchemy.orm as orm
from alembic import op
from sqlalchemy.future import select

# revision identifiers, used by Alembic.
revision = "0f07a3edd643"
down_revision = "9b0e597da71c"
branch_labels = None
depends_on = None

users_table = sa.table(
    "users", sa.column("name", sa.String), sa.column("role_id", sa.Integer)
)
roles_table = sa.table(
    "roles", sa.column("name", sa.String), sa.column("id", sa.Integer)
)
account_types_table = sa.table(
    "account_types", sa.column("name", sa.String), sa.column("id", sa.Integer)
)
user_role_association_table = sa.table(
    "user_role_association",
    sa.column("user_id", sa.ForeignKey("users.id")),
    sa.column("role_id", sa.ForeignKey("roles.id")),
)


def role_named(name):
    return (
        roles_table.select()
        .where(roles_table.c.name == op.inline_literal(name))
        .scalar_subquery()
    )


def account_type_named(name):
    return (
        account_types_table.select()
        .where(account_types_table.c.name == op.inline_literal(name))
        .scalar_subquery()
    )


def upgrade_users(session, oldrole, *newroles):
    for r in newroles:
        stmt = user_role_association_table.insert().values(role_id=role_named(r))
        print(stmt)
        print("---")
        # session.execute(stmt)


def downgrade_users(session: orm.Session, newrole: str, oldrole: str):
    stmt = (
        users_table.update()
        .where(user_role_association_table.c.role_id == role_named(newrole))
        .values(role_id=account_type_named(oldrole).c.id)
    )
    print(stmt)
    # session.execute(stmt)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    upgrade_users(session, "admin", "admin", "mentor", "display", "visible")
    upgrade_users(session, "mentor", "mentor", "display", "visible")
    upgrade_users(session, "display", "display", "autoload")
    upgrade_users(session, "lead", "lead", "student", "funds", "visible")
    upgrade_users(session, "student", "student", "funds", "visible")
    upgrade_users(session, "guardian_limited", "guardian")
    upgrade_users(session, "guardian", "guardian", "visible")

    session.commit()
    return

    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.drop_column("role_id")

    # ### end Alembic commands ###


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    downgrade_users(session, "admin", "admin")
    downgrade_users(session, "guardian", "guardian")
    downgrade_users(session, "student", "student")
    downgrade_users(session, "lead", "lead")
    downgrade_users(session, "autoload", "display")
    downgrade_users(session, "mentor", "mentor")
    downgrade_users(session, "admin", "admin")
    return

    session.flush()

    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("role_id", sa.INTEGER(), nullable=False))
        batch_op.create_foreign_key(None, "account_types", ["role_id"], ["id"])

    # ### end Alembic commands ###
