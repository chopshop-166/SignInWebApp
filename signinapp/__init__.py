#!/usr/bin/env python

import datetime
import os

import flask_excel as excel
from flask import Flask, render_template
from flask_assets import Bundle, Environment
from flask_bootstrap import Bootstrap5
from get_docker_secret import get_docker_secret
import yaml

from .admin import admin
from .auth import auth, login_manager
from .event import eventbp
from .events import events
from .mentor import mentor
from .model import Badge, Event, EventType, Role, Subteam, User, db
from .search import search
from .team import team
from .user import user

app = Flask(__name__)

class Config(object):
    TITLE = "Chop Shop Sign In"
    BLURB = """
We are Merrimack High School FIRST Robotics Competition Team 166, Chop Shop, from Merrimack, New Hampshire.
Our mission is to build teamwork and a great robot, along with fostering a love for Science, Technology, Engineering, and Mathematics.""".strip()
    DB_NAME = "signin.db"
    TIME_ZONE = "America/New_York"

class DebugConfig(Config):
    TITLE = "Chop Shop Sign In (debug)"
    DB_NAME = ':memory:'

# First load the default config...
if app.config["DEBUG"]:
    app.config.from_object(DebugConfig)
else:
    app.config.from_object(Config)
# ...then load the config file if it exists...
rv = os.environ.get("CSSIGNIN_CONFIG")
if rv:
    app.config.from_file(rv, load=yaml.safe_load, silent=True)
# ...then load from environment variables...
app.config.from_prefixed_env()
# ...finally load the secret key
app.secret_key = get_docker_secret("FLASK_SECRET_KEY", default="1234")

app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///' + app.config['DB_NAME'])
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', True)

scss = Bundle('custom.scss',
              filters='libsass,cssmin',
              depends="scss/*.scss",
              output='custom.generated.css')
assets = Environment(app)
assets.register('custom_css', scss)

excel.init_excel(app)

bootstrap = Bootstrap5(app)

login_manager.login_view = "auth.login"
login_manager.init_app(app)

db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(admin)
app.register_blueprint(auth)
app.register_blueprint(eventbp)
app.register_blueprint(events)
app.register_blueprint(mentor)
app.register_blueprint(search)
app.register_blueprint(team)
app.register_blueprint(user)


@app.route("/")
def index():
    events = Event.query.filter_by(is_active=True).all()
    return render_template("index.html.jinja2", events=events)


def init_default_db():

    ADMIN = Role(name="admin", mentor=True, can_display=True, admin=True)
    MENTOR = Role(name="mentor", mentor=True, can_display=True)
    DISPLAY = Role(name="display", can_display=True, autoload=True)
    LEAD = Role(name="lead", can_see_subteam=True)
    STUDENT = Role(name="student", default_role=True)

    TRAINING = EventType(
        name="Training", description="Training Session", autoload=True)
    BUILD = EventType(
        name="Build", description="Build Season", autoload=True)
    FUNDRAISER = EventType(name="Fundraiser", description="Fundraiser")
    COMPETITION = EventType(name="Competition", description="Competition")

    SOFTWARE = Subteam(name="Software")
    MECH = Subteam(name="Mechanical")
    CAD = Subteam(name="CAD")
    MARKETING = Subteam(name="Marketing")
    OUTREACH = Subteam(name="Outreach")

    db.session.add_all([
        ADMIN, MENTOR, DISPLAY, LEAD, STUDENT,
        TRAINING, BUILD, FUNDRAISER, COMPETITION,
        SOFTWARE, MECH, CAD, MARKETING, OUTREACH
    ])
    db.session.commit()

    admin_user = User.make("admin", password="1234", role=ADMIN, approved=True)
    display = User.make("display", password="1234",
                        role=DISPLAY, approved=True)
    db.session.add_all([admin_user, display])
    db.session.commit()


if app.config["DEBUG"]:
    with app.app_context():
        init_default_db()

        training = Event(
            name="Training",
            code="5678",
            start=datetime.datetime.fromisoformat("2022-01-01T00:00:00"),
            end=datetime.datetime.fromisoformat("2022-05-01T23:59:59"),
            type_=EventType.query.filter_by(name="Training").one()
        )
        notTraining = Event(
            name="Not Training",
            code="5679",
            start=datetime.datetime.fromisoformat("2022-01-01T00:00:00"),
            end=datetime.datetime.fromisoformat("2022-03-01T23:59:59"),
            type_=EventType.query.filter_by(name="Build").one()
        )
        db.session.add_all([training])
        db.session.commit()

        MENTOR = Role.from_name("mentor")
        STUDENT = Role.from_name("student")
        SOFTWARE = Subteam.from_name("Software")

        mentor = User.make("Matt Soucy", password="1234", role=MENTOR)
        mentor.approved = True
        student = User.make("Jeff Burke", password="1234",
                            role=STUDENT, subteam=SOFTWARE)
        student.approved = True
        safe = Badge(name="Safety Certified",
                     icon="cone-striped", color="orange",
                     description="Passed Safety Training")
        db.session.add_all([mentor, student, safe])
        db.session.commit()

        mentor.award_badge(safe.id)
        db.session.commit()
