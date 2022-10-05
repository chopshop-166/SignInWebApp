# Entry point for the application.
import click
from flask.cli import with_appcontext
from sqlalchemy.future import select

# For application discovery by the 'flask' command.
from . import app, init_default_db, db

# For import side-effects of setting up routes.
from . import auth, event, model, team, user


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

    for user in db.session.scalars(select(model.User)):
        user.code = model.gen_code()

    db.session.commit()

    click.echo("Generated new user codes for all users.")


app.cli.add_command(init_db_command)
app.cli.add_command(gen_codes_command)

if __name__ == "__main__":
    app.run()
