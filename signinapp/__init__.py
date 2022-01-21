#!/usr/bin/env python

from flask import Flask
from flask_bootstrap import Bootstrap5
from .model import SqliteModel, db, Person
import flask_excel as excel

from .model import model
from .views import qrbp

app = Flask(__name__)

#db_name = 'signin.db'
db_name = ':memory:'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

excel.init_excel(app)

bootstrap = Bootstrap5(app)
db.init_app(app)
with app.app_context():
    db.create_all()
app.register_blueprint(qrbp)

if app.config["DEBUG"]:
    with app.app_context():
        p = Person.make("Matt Soucy", mentor=True)
        db.session.add(p)
        db.session.commit()