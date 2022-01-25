# Entry point for the application.
import click
from flask.cli import with_appcontext

# For application discovery by the 'flask' command.
from . import app, init_default_db
# For import side-effects of setting up routes.
from . import auth, model, team, user, views
from .model import db


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""

    db.create_all()
    init_default_db()

    click.echo('Initialized the database.')


app.cli.add_command(init_db_command)

if __name__ == '__main__':
    app.run()
