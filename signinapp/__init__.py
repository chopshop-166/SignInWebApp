#!/usr/bin/env python

from flask import Flask
from flask_bootstrap import Bootstrap5
import flask_excel as excel

import os

from .auth import auth, login_manager
from .model import AccountType, Person, SqliteModel, db, model
from .views import qrbp

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "1234")

if app.config["DEBUG"]:
    db_name = ':memory:'
else:
    db_name = 'signin.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

excel.init_excel(app)

bootstrap = Bootstrap5(app)
login_manager.init_app(app)

db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(qrbp)

app.register_blueprint(auth)
login_manager.login_view = "auth.login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return Person.query.get(int(user_id))


if app.config["DEBUG"]:
    with app.app_context():

        ADMIN = AccountType(name="admin", mentor=True)
        MENTOR = AccountType(name="mentor", mentor=True)
        DISPLAY = AccountType(name="display")
        STUDENT = AccountType(name="student")
        db.session.add_all([ADMIN, MENTOR, DISPLAY, STUDENT])
        db.session.commit()

        admin = Person.make("admin", password="1234", role=ADMIN)
        db.session.add(admin)
        db.session.commit()
