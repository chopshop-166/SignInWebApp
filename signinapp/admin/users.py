from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import (BooleanField, PasswordField, SelectField, StringField,
                     SubmitField)
from wtforms.validators import DataRequired, EqualTo

from ..model import Role, Subteam, User, db
from ..util import admin_required
from .util import admin


class UserForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    password = PasswordField()
    role = SelectField()
    subteam = SelectField()
    approved = BooleanField()
    active = BooleanField()
    submit = SubmitField()


class DeleteUserForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    verify = StringField("Confirm Name",
                         validators=[DataRequired(),
                                     EqualTo("name", message="Enter the user's name")])
    submit = SubmitField()


@admin.route("/admin/users")
@admin_required
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template("admin/users.html.jinja2", users=users, roles=roles)


@admin.route("/admin/users/approve", methods=["POST"])
@admin_required
def user_approve():
    user_id = request.args.get("user_id", None)
    user = User.query.get(user_id)
    if user:
        user.approved = True
        db.session.commit()
    else:
        flash("Invalid user ID")
    return redirect(url_for("admin.users"))


@admin.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = UserForm()
    form.role.choices = [(r.id, r.name) for r in Role.query.all()]
    form.subteam.choices = [(0, "None")]+[(s.id, s.name)
                                          for s in Subteam.query.all()]

    if form.validate_on_submit():
        user = User.make(
            name=form.name.data,
            password=form.password.data,
            approved=form.approved.data,
            role=Role.query.get(form.role.data)
        )
        if form.subteam.data:
            user.subteam_id = form.subteam.data
        user.active = form.active.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("admin.users"))

    return render_template("admin/form.html.jinja2", form=form,
                           title=f"New User - Chop Shop Sign In")


@admin.route("/admin/users/edit", methods=["GET", "POST"])
@admin_required
def edit_user():
    user : User = User.query.get(request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("admin.users"))

    form = UserForm(obj=user)
    form.role.choices = [(r.id, r.name) for r in Role.query.all()]
    form.subteam.choices = [(0, "None")]+[(s.id, s.name)
                                          for s in Subteam.query.all()]

    if form.validate_on_submit():
        # Cannot use form.populate_data because of the password
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role_id = form.role.data
        user.subteam_id = form.subteam.data or None
        user.approved = form.approved.data
        user.active = form.active.data
        db.session.commit()
        return redirect(url_for("admin.users"))

    form.role.process_data(user.role_id)
    form.subteam.process_data(user.subteam_id)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit User {user.name} - Chop Shop Sign In")


@admin.route("/admin/users/delete", methods=["GET", "POST"])
@admin_required
def delete_user():
    form = DeleteUserForm()
    user = User.query.get(request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("admin.users"))

    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("admin.users"))

    form.name.process_data(user.name)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Delete User {user.name} - Chop Shop Sign In")
