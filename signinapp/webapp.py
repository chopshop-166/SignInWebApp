# Entry point for the application.
import click
from flask.cli import with_appcontext
from sqlalchemy.future import select

# For application discovery by the 'flask' command.
from . import app, db, init_default_db, model


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""

    model.db.create_all()
    init_default_db()

    click.echo("Initialized the database.")


@click.command("gen-codes")
@with_appcontext
def gen_codes_command():
    """Generate user codes for all users."""

    for u in db.session.scalars(select(model.User)):
        u.code = model.gen_code()

    db.session.commit()

    click.echo("Generated new user codes for all users.")


@click.command("generate-secret")
@with_appcontext
def generate_secret_command():
    """Generate a secret key."""

    import secrets

    click.echo(secrets.token_hex())


@click.command("trim-stamps")
@with_appcontext
def trim_stamps_command():
    all_stamps: list[model.Stamps] = db.session.scalars(select(model.Stamps))
    for stamp in all_stamps:
        start_time = stamp.event.adjusted_start
        if stamp.start < start_time:
            click.echo(
                f"Adjusting start stamp for event {stamp.id} from {stamp.start} to {start_time}"
            )
            stamp.start = start_time
        end_time = stamp.event.adjusted_end
        if stamp.end > end_time:
            click.echo(
                f"Adjusting end stamp for event {stamp.id} from {stamp.end} to {end_time}"
            )
            stamp.end = end_time

    db.session.commit()


@click.command("debug-sql")
@with_appcontext
def debug_sql_command():
    from .model import AccountType, User
    from sqlalchemy import update

    stmt = select(AccountType.id).where(AccountType.admin == True)
    # print(stmt)
    admin_stmt = (
        select(AccountType.id).where(AccountType.name == "admin").scalar_subquery()
    )
    stmt = update(User).where(User.role.has(name="admin")).values(role_id=admin_stmt)
    print(stmt)


app.cli.add_command(init_db_command)
app.cli.add_command(gen_codes_command)
app.cli.add_command(generate_secret_command)
app.cli.add_command(trim_stamps_command)
app.cli.add_command(debug_sql_command)

if __name__ == "__main__":
    app.run()
