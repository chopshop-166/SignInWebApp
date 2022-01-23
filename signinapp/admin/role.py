#!/usr/bin/env python

from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Role, db
from .util import admin, admin_required


class RoleForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    admin = BooleanField()
    mentor = BooleanField()
    can_display = BooleanField("Can display event pages")
    autoload = BooleanField("Automatically load event pages")
    can_see_subteam = BooleanField("Can view subteam stamps")
    submit = SubmitField()


@admin.route("/admin/subteams", methods=["GET", "POST"])
@admin_required
def roles():
    roles = Role.query.all()
    return render_template("admin/roles.html.jinja2", roles=roles)


@admin.route("/admin/subteams/new", methods=["GET", "POST"])
@admin_required
def new_role():
    form = RoleForm()

    if form.validate_on_submit():
        r = Role(
            name=form.name.data,
            admin=form.admin.data,
            mentor=form.mentor.data,
            can_display=form.can_display.data,
            autoload=form.autoload.data,
            can_see_subteam=form.can_see_subteam.data
        )
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template("admin/form.html.jinja2", form=form,
                           title=f"New Subteam - Chop Shop Sign In")


@admin.route("/admin/subteams/edit", methods=["GET", "POST"])
@admin_required
def edit_role():
    form = RoleForm()
    r = Role.query.get(request.args["role_id"])

    if not r:
        flash("Invalid role ID")
        return redirect(url_for("admin.roles"))

    if form.validate_on_submit():
        r.name=form.name.data
        r.admin=form.admin.data
        r.mentor=form.mentor.data
        r.can_display=form.can_display.data
        r.autoload=form.autoload.data
        r.can_see_subteam=form.can_see_subteam.data
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    form.name.process_data(r.name)
    form.admin.process_data(r.admin)
    form.mentor.process_data(r.mentor)
    form.can_display.process_data(r.can_display)
    form.autoload.process_data(r.autoload)
    form.can_see_subteam.process_data(r.can_see_subteam)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit Role {r.name} - Chop Shop Sign In")
