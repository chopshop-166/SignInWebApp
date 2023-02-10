#!/usr/bin/env python

import datetime
import locale
import os
import zoneinfo

import flask_excel as excel
import yaml
from flask import Flask, render_template
from flask_assets import Bundle, Environment
from flask_bootstrap import Bootstrap5
from flask_migrate import Migrate
from sqlalchemy.future import select

from . import (
    active,
    admin,
    auth,
    badge,
    dbadmin,
    event,
    events,
    qr,
    search,
    team,
    user,
    finance,
)
from .auth import login_manager
from .jobs import scheduler
from .model import (
    Active,
    Badge,
    Event,
    EventType,
    Guardian,
    Role,
    Student,
    Subteam,
    User,
    db,
)

locale.setlocale(locale.LC_ALL, "")

app = Flask(__name__)


class Config(object):
    TITLE = "Chop Shop Sign In"
    BLURB = """
We are Merrimack High School FIRST Robotics Competition Team 166, Chop Shop, from Merrimack, New Hampshire.
Our mission is to build teamwork and a great robot, along with fostering a love for Science, Technology, Engineering, and Mathematics.""".strip()
    DB_NAME = "signin.db"
    TIME_ZONE = "America/New_York"
    SECRET_KEY = "1234"
    PRE_EVENT_ACTIVE_TIME = 30
    POST_EVENT_ACTIVE_TIME = 120
    AUTO_SIGNOUT_BEHAVIOR = "None"  # Valid Options (Credit, Discard, None)


class DebugConfig(Config):
    TITLE = "Chop Shop Sign In (debug)"
    DB_NAME = ":memory:"


# First load the default config...
if app.config["DEBUG"]:
    app.config.from_object(DebugConfig)
else:
    app.config.from_object(Config)
# ...then load the config file if it exists...
rv = os.environ.get("CSSIGNIN_CONFIG")
if rv:
    app.config.from_file(rv, load=yaml.safe_load, silent=True)
# ...then load from environment variables
app.config.from_prefixed_env()

# Now validate the config
assert app.config["TITLE"], "Invalid title given in config"
assert (
    app.config["TIME_ZONE"] in zoneinfo.available_timezones()
), "Invalid time zone given in config"
assert (
    app.config["PRE_EVENT_ACTIVE_TIME"] >= 0
), "Invalid pre active time given in config"
assert (
    app.config["POST_EVENT_ACTIVE_TIME"] >= 0
), "Invalid post active time given in config"
assert app.config["AUTO_SIGNOUT_BEHAVIOR"] in (
    "Credit",
    "Discard",
    "None",
), "Invalid sign out behavior given in config"

app.config.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///" + app.config["DB_NAME"])
app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", True)

scss = Bundle(
    "custom.scss",
    filters="libsass,cssmin",
    depends="scss/*.scss",
    output="custom.generated.css",
)
assets = Environment(app)
assets.register("custom_css", scss)

excel.init_excel(app)

bootstrap = Bootstrap5(app)

login_manager.login_view = "auth.login"
login_manager.init_app(app)

db.init_app(app)
with app.app_context():
    db.create_all()

migrate = Migrate(app, db)

scheduler.init_app(app)
scheduler.start()

active.init_app(app)
admin.init_app(app)
auth.init_app(app)
badge.init_app(app)
dbadmin.init_app(app)
event.init_app(app)
events.init_app(app)
finance.init_app(app)
qr.init_app(app)
search.init_app(app)
team.init_app(app)
user.init_app(app)


@app.route("/")
def index():
    stmt = select(Event).filter_by(is_active=True)
    events = db.session.scalars(stmt)
    return render_template("index.html.jinja2", events=events)


@app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "error.html.jinja2", error_headline="Page Not Found", error_msg=e
        ),
        404,
    )


@app.errorhandler(500)
def internal_server_error(e: int):
    return (
        render_template(
            "error.html.jinja2", error_headline="Internal Error", error_msg=e
        ),
        500,
    )


@app.errorhandler(Exception)
def internal_server_error_ex(e: Exception):
    import io
    import traceback

    buffer = io.StringIO()

    traceback.print_exception(e)
    traceback.print_exception(e, file=buffer)
    return (
        render_template(
            "error.html.jinja2",
            error_headline="Internal Error",
            error_msg=buffer.getvalue(),
        ),
    )


def create_if_not_exists(cls, name, **kwargs):
    if not cls.from_name(name):
        item = cls(name=name, **kwargs)
        db.session.add(item)


def init_default_db():
    create_if_not_exists(Role, name="admin", mentor=True, can_display=True, admin=True)
    create_if_not_exists(Role, name="mentor", mentor=True, can_display=True)
    create_if_not_exists(Role, name="display", can_display=True, autoload=True)
    create_if_not_exists(Role, name="lead", can_see_subteam=True, receives_funds=True)
    create_if_not_exists(Role, name="student", default_role=True, receives_funds=True)
    create_if_not_exists(Role, name="guardian_limited", guardian=True, visible=False)
    create_if_not_exists(Role, name="guardian", guardian=True)

    create_if_not_exists(
        EventType, name="Training", description="Training Session", autoload=True
    )
    create_if_not_exists(
        EventType, name="Build", description="Build Season", autoload=True
    )
    create_if_not_exists(EventType, name="Fundraiser", description="Fundraiser")
    create_if_not_exists(EventType, name="Competition", description="Competition")

    create_if_not_exists(Subteam, name="Software")
    create_if_not_exists(Subteam, name="Mechanical")
    create_if_not_exists(Subteam, name="CAD")
    create_if_not_exists(Subteam, name="Marketing")
    create_if_not_exists(Subteam, name="Outreach")

    db.session.commit()

    if not db.session.scalar(select(User).filter_by(username="admin")):
        User.make("admin", "admin", password="1234", role="admin", approved=True)
    if not db.session.scalar(select(User).filter_by(username="display")):
        User.make("display", "display", password="1234", role="display", approved=True)
    db.session.commit()


if app.config["DEBUG"]:
    with app.app_context():
        init_default_db()

        now = datetime.datetime.now(tz=datetime.timezone.utc).replace(microsecond=0)
        offset = datetime.timedelta(hours=3)
        training = Event.create(
            name="Training",
            description="Test Training Event",
            location="D124",
            code="5678",
            start=now,
            end=now + offset,
            event_type="Training",
        )
        notTraining = Event.create(
            name="Not Training",
            description="Test Build Event",
            location="D124",
            code="5679",
            start=now,
            end=now + offset,
            event_type="Build",
        )

        expired_event = Event.create(
            name="Ended Training",
            description="Test Training Event",
            location="D124",
            code="8765",
            start=now - offset,
            end=now
            - datetime.timedelta(minutes=app.config["POST_EVENT_ACTIVE_TIME"] - 5),
            event_type="Build",
        )
        db.session.commit()

        mentor_user = User.make(
            "msoucy",
            "Matt Soucy",
            preferred_name="Matt",
            code="code-msoucy",
            phone_number="603 555-5555",
            email="first@test.com",
            address="123 First Street",
            tshirt_size="Large",
            password="1234",
            role="mentor",
            approved=True,
        )
        student_user = Student.make(
            "jburke",
            "Jeff Burke",
            preferred_name="Jeff",
            code="code-jburke",
            password="1234",
            graduation_year=2022,
            subteam="Software",
            approved=True,
            tshirt_size="Large",
        )
        student_user.student_user_data.add_guardian(
            guardian=Guardian.get_from(
                name="Parent Burke",
                phone_number="(603)555-5555",
                email="test@email.com",
                contact_order=1,
            )
        )

        student_training_event = Active(
            user_id=student_user.id, event_id=expired_event.id, start=now - offset
        )
        db.session.add(student_training_event)

        safe = Badge(
            name="Safety Certified",
            icon="cone-striped",
            color="#FFA500",  # Orange - needs to be in hex format for WTForms
            description="Passed Safety Training",
        )
        db.session.add(safe)
        db.session.commit()

        mentor_user.award_badge(safe)
        db.session.commit()
