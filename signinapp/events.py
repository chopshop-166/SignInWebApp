from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib import parse

from dateutil.rrule import WEEKLY, rrule
from flask import Blueprint, Flask, flash, redirect, request, url_for
from flask.templating import render_template
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func
from sqlalchemy.future import select
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    FieldList,
    Form,
    FormField,
    HiddenField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import DataRequired

from .mentor import mentor_required
from .model import Event, EventRegistration, EventType, db, gen_code, get_form_ids
from .util import correct_time_for_storage, correct_time_from_storage

events = Blueprint("events", __name__)

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M",
]

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class EventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    location = StringField()
    code = StringField(validators=[DataRequired()])
    start = DateTimeLocalField(format=DATE_FORMATS)
    end = DateTimeLocalField(format=DATE_FORMATS)
    type_id = SelectField(label="Type", choices=lambda: get_form_ids(EventType))
    enabled = BooleanField(default=True)
    registration_open = BooleanField(
        default=False, description="Whether this event shows up for users to register"
    )
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start.data >= self.end.data:
            self.end.errors.append("End time must not be before start time")
            return False

        return True


class BulkEventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    location = StringField()
    start_day = DateField(validators=[DataRequired()])
    end_day = DateField(validators=[DataRequired()])
    days = SelectMultipleField(choices=WEEKDAYS, validators=[DataRequired()])
    start_time = TimeField(validators=[DataRequired()])
    end_time = TimeField(validators=[DataRequired()])
    type_id = SelectField(label="Type", choices=lambda: get_form_ids(EventType))
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start_time.data >= self.end_time.data:
            self.end_time.errors.append("End time must not be before start time")
            rv = False

        if self.start_day.data >= self.end_day.data:
            self.end_day.errors.append("End day must not be before start day")
            rv = False

        return rv


class EventSearchForm(FlaskForm):
    category = SelectField(choices=lambda: get_form_ids(EventType))
    submit = SubmitField()


class EventBlockForm(Form):
    start = DateTimeLocalField(render_kw={"readonly": True})
    end = DateTimeLocalField(render_kw={"readonly": True})
    register = BooleanField()
    block_id = HiddenField()
    comment = TextAreaField(
        "Comment",
        description="Comment on event signup",
        render_kw={"placeholder": "Comment"},
    )


class EventRegistrationForm(FlaskForm):
    blocks = FieldList(FormField(EventBlockForm))
    submit = SubmitField()


@events.route("/events/")
@mentor_required
def list_events():
    events: list[Event] = db.session.execute(
        select(Event).filter_by(enabled=True).order_by(Event.start)
    ).scalars()
    return render_template("events.html.jinja2", events=events)


@events.route("/events/previous")
@mentor_required
def list_previous_events():
    events: list[Event] = db.session.execute(
        select(Event)
        .filter_by(enabled=True)
        .order_by(Event.start)
        .where(Event.end <= func.now())
    ).scalars()
    return render_template("events.html.jinja2", prefix="Previous ", events=events)


@events.route("/events/active")
@mentor_required
def list_active_events():
    events: list[Event] = db.session.execute(
        select(Event)
        .filter_by(enabled=True)
        .order_by(Event.start)
        .where(Event.is_active)
    ).scalars()
    return render_template("events.html.jinja2", prefix="Active ", events=events)


@events.route("/events/today")
@mentor_required
def list_todays_events():
    events: list[Event] = db.session.execute(
        select(Event)
        .filter_by(enabled=True)
        .order_by(Event.start)
        .where(
            Event.start < func.datetime("now", "+1 day", "start of day"),
            Event.end > func.datetime("now", "start of day"),
        )
    ).scalars()
    return render_template("events.html.jinja2", prefix="Today's ", events=events)


@events.route("/events/upcoming")
@mentor_required
def list_upcoming_events():
    events: list[Event] = db.session.execute(
        select(Event)
        .filter_by(enabled=True)
        .order_by(Event.start)
        .where(Event.start > func.now())
    ).scalars()
    return render_template("events.html.jinja2", prefix="Upcoming ", events=events)


@events.route("/events/open")
def list_open_events():
    events: list[Event] = db.session.execute(
        select(Event)
        .filter_by(enabled=True, registration_open=True)
        .order_by(Event.start)
        .where(Event.end > func.now())
    ).scalars()

    return render_template("open_events.html.jinja2", events=events)


@events.route("/events/stats")
@mentor_required
def event_stats():
    event: Event = db.session.get(Event, request.args["event_id"])
    users = defaultdict(timedelta)
    subteams = defaultdict(timedelta)
    blocks = defaultdict(list)
    for stamp in event.stamps:
        users[stamp.user] += stamp.elapsed
        subteams[stamp.user.subteam] += stamp.elapsed
    now = datetime.now(tz=timezone.utc)
    for active in event.active:
        users[active.user] += now - correct_time_from_storage(active.start)
        subteams[active.user.subteam] += now - correct_time_from_storage(active.start)

    for block in event.blocks:
        for registration in block.registrations:
            if registration.registered:
                blocks[block].append((registration.user.name, registration.comment))
        # Sort user names
        blocks[block] = sorted(blocks[block], key=lambda registration: registration[0])

    blocks = sorted(
        blocks.items(),
        key=lambda block: block[0].start,
    )

    users = sorted(((u.name, t) for u, t in users.items()))
    subteams = sorted(((s.name, t) for s, t in subteams.items() if s))
    registration_url = parse.urljoin(
        request.host_url, url_for("events.register_event", event_id=event.id)
    )
    return render_template(
        "event_stats.html.jinja2",
        event=event,
        users=users,
        subteams=subteams,
        blocks=blocks,
        registration_url=registration_url,
    )


@events.route("/events/bulk", methods=["GET", "POST"])
@mentor_required
def bulk_events():
    form = BulkEventForm()

    if form.validate_on_submit():
        start_time = datetime.combine(form.start_day.data, form.start_time.data)
        end_time = datetime.combine(form.end_day.data, form.end_time.data)
        days = rrule(
            WEEKLY, byweekday=[WEEKDAYS.index(d) for d in form.days.data]
        ).between(start_time, end_time, inc=True)
        event_type = db.session.get(EventType, form.type_id.data)
        for d in [d.date() for d in days]:
            Event.create(
                name=form.name.data,
                description=form.description.data,
                location=form.location.data,
                start=datetime.combine(d, form.start_time.data),
                end=datetime.combine(d, form.end_time.data),
                event_type=event_type,
            )
        db.session.commit()

        return redirect(url_for("events.list_events"))
    return render_template("form.html.jinja2", form=form, title="Bulk Event Add")


@events.route("/events/new", methods=["GET", "POST"])
@mentor_required
def new_event():
    form = EventForm()
    if form.validate_on_submit():

        event_type = db.session.get(EventType, form.type_id.data)
        Event.create(
            name=form.name.data,
            description=form.description.data,
            location=form.location.data,
            start=form.start.data,
            end=form.end.data,
            event_type=event_type,
        )
        db.session.commit()

        return redirect(url_for("events.list_events"))

    form.code.process_data(gen_code())
    return render_template("form.html.jinja2", form=form, title="New Event")


@events.route("/events/edit", methods=["GET", "POST"])
@mentor_required
def edit_event():
    event = db.session.get(Event, request.args["event_id"])
    if not event:
        flash("Event does not exist")
        return redirect(url_for("events.list_events"))

    form = EventForm(obj=event)
    # Only re-format the times when initialy sending the form.
    if not form.is_submitted():
        form.start.data = correct_time_from_storage(form.start.data)
        form.end.data = correct_time_from_storage(form.end.data)

    if form.validate_on_submit():
        form.start.data = correct_time_for_storage(form.start.data)
        form.end.data = correct_time_for_storage(form.end.data)
        form.populate_obj(event)
        db.session.commit()
        return redirect(url_for("events.list_events"))

    form.type_id.process_data(event.type_id)
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Event {event.name}",
    )


@events.route("/events/search", methods=["GET", "POST"])
@mentor_required
def search():
    form = EventSearchForm()

    if form.validate_on_submit():
        event_type = db.session.get(EventType, form.category.data)
        results = db.session.scalars(select(Event).where(Event.type_ == event_type))
        return render_template("search/events.html.jinja2", form=form, results=results)

    return render_template("search/hours.html.jinja2", form=form, results=None)


@events.route("/events/register", methods=["GET", "POST"])
def register_event():
    event: list[Event] = db.session.get(Event, request.args["event_id"])
    if not event:
        flash("Event does not exist, please double check the URL")
        return redirect(url_for("index"))

    data = {"blocks": []}
    for block in event.blocks:
        registration = db.session.scalar(
            select(EventRegistration).filter_by(user=current_user, event_block=block)
        )
        # If no registration exists for this block, or they've chosen not to register for this event block
        registered = registration and registration.registered
        comment = registration.comment if registration else ""
        data["blocks"].append(
            {
                "data": {
                    "start": correct_time_from_storage(block.start),
                    "end": correct_time_from_storage(block.end),
                    "block_id": block.id,
                    "register": registered,
                    "comment": comment,
                }
            }
        )
    form = EventRegistrationForm(data=data)

    if form.validate_on_submit():
        for block in form.blocks.data:
            EventRegistration.upsert(
                event_block_id=block["block_id"],
                user=current_user,
                comment=block["comment"],
                registered=block["register"],
            )
        db.session.commit()
        flash(f"Successfully Signed up for {event.name}")
        return redirect(url_for("index"))

    return render_template(
        "event_register.html.jinja2",
        event=event,
        form=form,
        title=f"Register Event {event.name}",
    )


def init_app(app: Flask):
    app.register_blueprint(events)
