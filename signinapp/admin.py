#!/usr/bin/env python

from functools import wraps
from http import HTTPStatus

from flask import (Blueprint, Response, current_app, flash, redirect, request,
                   url_for)
from flask.templating import render_template
from flask_login import LoginManager, current_user
from flask_login.config import EXEMPT_METHODS
from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from .model import Event, EventType, Person, Role, db, event_code

login_manager = LoginManager()

admin = Blueprint("admin", __name__)

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']


class EventForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    code = StringField(validators=[DataRequired()])
    start = DateTimeLocalField(format=DATE_FORMATS)
    end = DateTimeLocalField(format=DATE_FORMATS)
    type_ = SelectField(label="Type")
    submit = SubmitField()


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method in EXEMPT_METHODS or \
                current_app.config.get('LOGIN_DISABLED'):
            pass
        elif not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        elif not current_user.admin:
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
    users = Person.query.all()
    roles = Role.query.all()
    return render_template("admin_main.html")


@admin.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    users = Person.query.all()
    roles = Role.query.all()
    return render_template("admin_user.html.jinja2", users=users, roles=roles)


@admin.route("/admin/users/update_role", methods=["POST"])
@admin_required
def update_role():
    user = Person.query.get(int(request.form["user_id"]))
    if not user:
        flash("Invalid user ID")
        return Response("Invalid user ID", HTTPStatus.BAD_REQUEST)

    role = Role.query.get(int(request.form["role"]))
    if role:
        flash("Invalid role ID")
        return Response("Invalid role ID", HTTPStatus.BAD_REQUEST)

    user.role_id = role.id
    db.session.commit()
    return redirect(url_for("admin.admin_users"))


@admin.route("/admin/events")
@admin_required
def admin_events():
    events = Event.query.filter_by(enabled=True).all()
    return render_template("admin_events.html.jinja2", events=events)


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
            type_=EventType.query.get(form.type_.data)
        )
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for("admin.admin_events"))
    form.code.data = event_code()
    return render_template("admin_event.html.jinja2", form=form)


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
        db.session.commit()
        return redirect(url_for("admin.admin_events"))

    form.name.process_data(event.name)
    form.description.process_data(event.description)
    form.code.process_data(event.code)
    form.start.process_data(event.start)
    form.end.process_data(event.end)
    form.type_.process_data(event.type_id)
    return render_template("admin_event.html.jinja2", form=form)
