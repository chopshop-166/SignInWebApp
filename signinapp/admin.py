#!/usr/bin/env python

from datetime import datetime
from functools import wraps
from http import HTTPStatus

from dateutil.rrule import rrule, WEEKLY
from flask import (Blueprint, Response, current_app, flash, redirect, request,
                   url_for)
from flask.templating import render_template
from flask_login import LoginManager, current_user
from flask_login.config import EXEMPT_METHODS
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import (BooleanField, DateField, DateTimeLocalField, IntegerField,
                     PasswordField, SelectField, SelectMultipleField,
                     StringField, SubmitField, TimeField)
from wtforms.validators import DataRequired, ValidationError

from .model import (Active, Event, EventType, Person, Role, Stamps, db,
                    event_code)

login_manager = LoginManager()

admin = Blueprint("admin", __name__)

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']

WEEKDAYS = ["Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday", "Sunday"]


class EventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    code = StringField(validators=[DataRequired()])
    start = DateTimeLocalField(format=DATE_FORMATS)
    end = DateTimeLocalField(format=DATE_FORMATS)
    type_ = SelectField(label="Type")
    enabled = BooleanField(default=True)
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start.data >= self.end.data:
            self.end.errors.append('End time must not be before start time')
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
    type_ = SelectField(label="Type")
    submit = SubmitField()

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if self.start_time.data >= self.end_time.data:
            self.end_time.errors.append(
                'End time must not be before start time')
            rv = False

        if self.start_day.data >= self.end_day.data:
            self.end_day.errors.append('End day must not be before start day')
            rv = False

        return rv


class UserForm(FlaskForm):
    name = StringField()
    password = PasswordField()
    role = SelectField()
    submit = SubmitField()


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method in EXEMPT_METHODS or \
                current_app.config.get('LOGIN_DISABLED'):
            pass
        elif not current_user.is_authenticated or not current_user.admin:
            return current_app.login_manager.unauthorized()
        try:
            # current_app.ensure_sync available in Flask >= 2.0
            return current_app.ensure_sync(func)(*args, **kwargs)
        except AttributeError:
            return func(*args, **kwargs)
    return decorated_view


@admin.route("/admin")
@admin_required
def admin_main():
    return render_template("admin_main.html.jinja2")


@admin.route("/admin/users", methods=["GET", "POST"])
@admin_required
def users():
    users = Person.query.all()
    roles = Role.query.all()
    return render_template("admin/users.html.jinja2", users=users, roles=roles)


@admin.route("/admin/users/edit", methods=["GET", "POST"])
@admin_required
def edit_user():
    form = UserForm()
    form.role.choices = [(t.id, t.name) for t in Role.query.all()]
    user = Person.query.get(request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return Response("Invalid user ID", HTTPStatus.BAD_REQUEST)

    if form.validate_on_submit():
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role_id = form.role.data
        db.session.commit()

    form.name.process_data(user.name)
    form.role.process_data(user.role_id)
    return render_template("admin/user.html.jinja2", form=form)


@admin.route("/admin/event")
@admin_required
def events():
    events = Event.query.filter_by(enabled=True).all()
    return render_template("admin/events.html.jinja2", events=events)


@admin.route("/admin/event/bulk", methods=["GET", "POST"])
@admin_required
def bulk_events():
    form = BulkEventForm()
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]

    if form.validate_on_submit():
        start_time = datetime.combine(form.start_day.data, form.start_time.data)
        end_time = datetime.combine(form.end_day.data, form.end_time.data)
        days = rrule(WEEKLY,
            byweekday=[WEEKDAYS.index(d) for d in form.days.data]
        ).between(start_time, end_time, inc=True)
        for d in [d.date() for d in days]:
            ev = Event(
                name=form.name.data,
                description=form.description.data,
                start=datetime.combine(d, form.start_time.data),
                end=datetime.combine(d, form.end_time.data),
                code=event_code(),
                type_=EventType.query.get(form.type_.data)
            )
            db.session.add(ev)
        db.session.commit()

        return redirect(url_for("admin.events"))
    return render_template("admin/event.html.jinja2", form=form)


@admin.route("/admin/event/new", methods=["GET", "POST"])
@admin_required
def new_event():

    form = EventForm()
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]
    if form.validate_on_submit():
        ev = Event(
            name=form.name.data,
            description=form.description.data,
            start=form.start.data,
            end=form.end.data,
            code=form.code.data,
            type_=EventType.query.get(form.type_.data),
            enabled=form.enabled.data
        )
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for("admin.admin_events"))

    form.code.process_data(event_code())
    return render_template("admin/event.html.jinja2", form=form)


@admin.route("/admin/event/edit", methods=["GET", "POST"])
@admin_required
def edit_event():
    evid = request.args["event_id"]

    form = EventForm()
    form.type_.choices = [(t.id, t.name) for t in EventType.query.all()]
    event = Event.query.get(evid)

    if form.validate_on_submit():
        event.name = form.name.data
        event.description = form.description.data
        event.start = form.start.data
        event.end = form.end.data
        event.code = form.code.data
        event.type_ = EventType.query.get(form.type_.data)
        event.enabled = form.enabled.data
        db.session.commit()
        return redirect(url_for("admin.events"))

    form.name.process_data(event.name)
    form.description.process_data(event.description)
    form.code.process_data(event.code)
    form.start.process_data(event.start)
    form.end.process_data(event.end)
    form.type_.process_data(event.type_id)
    form.enabled.process_data(event.enabled)
    return render_template("admin/event.html.jinja2", form=form)


@admin.route("/admin/active", methods=["GET", "POST", "DELETE"])
@admin_required
def active():
    if request.method == "GET":
        actives = Active.query.all()
        return render_template("admin/active.html.jinja2", active=actives)
    elif request.method == "POST":
        active_event = Active.query.get(request.form["active_id"])
        stamp = Stamps(person=active_event.person,
                       event=active_event.event, start=active_event.start)
        db.session.delete(active_event)
        db.session.add(stamp)
        db.session.commit()
        return redirect(url_for("admin.active"))


@admin.route("/admin/active/delete", methods=["POST"])
@admin_required
def active_delete():
    active_event = Active.query.get(request.form["active_id"])
    db.session.delete(active_event)
    db.session.commit()
    return redirect(url_for("admin.active"))
