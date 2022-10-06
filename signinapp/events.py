from collections import defaultdict
from datetime import datetime, timedelta, timezone

from dateutil.rrule import WEEKLY, rrule
from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from wtforms import (
    BooleanField,
    DateField,
    DateTimeLocalField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TimeField,
)
from wtforms.validators import DataRequired

from .mentor import mentor_required
from .model import Event, EventType, db, event_code, get_form_ids
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
    code = StringField(validators=[DataRequired()])
    start = DateTimeLocalField(format=DATE_FORMATS)
    end = DateTimeLocalField(format=DATE_FORMATS)
    type_id = SelectField(label="Type")
    enabled = BooleanField(default=True)
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


@events.route("/events")
@mentor_required
def list_events():
    events: Event = db.session.execute(select(Event).filter_by(enabled=True)).scalars()
    return render_template("events.html.jinja2", events=events)


@events.route("/events/stats")
@mentor_required
def event_stats():
    event = db.session.get(Event, request.args["event_id"])
    users = defaultdict(timedelta)
    for stamp in event.stamps:
        users[stamp.user.name] += stamp.elapsed
    users = sorted(users.items())
    return render_template("event_stats.html.jinja2", event=event, users=users)


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
            ev = Event(
                name=form.name.data,
                description=form.description.data,
                start=correct_time_for_storage(
                    datetime.combine(d, form.start_time.data)
                ),
                end=correct_time_for_storage(datetime.combine(d, form.end_time.data)),
                code=event_code(),
                type_=event_type,
            )
            db.session.add(ev)
        db.session.commit()

        return redirect(url_for("events.list_events"))
    return render_template("form.html.jinja2", form=form, title="Bulk Event Add")


@events.route("/events/new", methods=["GET", "POST"])
@mentor_required
def new_event():
    form = EventForm()
    if form.validate_on_submit():
        ev = Event()
        form.start.data = correct_time_for_storage(form.start.data)
        form.end.data = correct_time_for_storage(form.end.data)
        form.populate_obj(ev)
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for("events.list_events"))

    form.code.process_data(event_code())
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
