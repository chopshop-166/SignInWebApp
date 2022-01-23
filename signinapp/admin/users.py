#!/usr/bin/env python

from http import HTTPStatus

from flask import Response, flash, request
from flask.templating import render_template
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Person, Role, Subteam, db
from .util import admin, admin_required


class UserForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    password = PasswordField()
    role = SelectField()
    subteam = SelectField()
    submit = SubmitField()


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
    form.role.choices = [(r.id, r.name) for r in Role.query.all()]
    form.subteam.choices = [(s.id, s.name) for s in Subteam.query.all()]
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
    form.subteam.process_data(user.subteam_id)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit User {user.name} - Chop Shop Sign In")
