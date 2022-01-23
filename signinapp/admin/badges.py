#!/usr/bin/env python

from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Badge, db
from .util import admin, admin_required


class BadgeForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    icon = StringField()
    color = StringField("Icon Color")
    submit = SubmitField()


@admin.route("/admin/badges", methods=["GET"])
@admin_required
def all_badges():
    badges = Badge.query.all()
    return render_template("admin/badges.html.jinja2", badges=badges)


@admin.route("/admin/badges/new", methods=["GET", "POST"])
@admin_required
def new_badge():

    form = BadgeForm()
    if form.validate_on_submit():
        badge = Badge(name=form.name.data,
                      description=form.description.data,
                      icon=form.icon.data,
                      color=form.color.data)
        db.session.add(badge)
        db.session.commit()
        return redirect(url_for("admin.all_badges"))

    return render_template("admin/form.html.jinja2", form=form,
                           title="New Badge - Chop Shop Sign In")


@admin.route("/admin/badges/edit", methods=["GET", "POST"])
@admin_required
def edit_badge():
    badge_id = request.args["badge_id"]

    form = BadgeForm()
    badge = Badge.query.get(badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("admin.all_badges"))

    if form.validate_on_submit():
        badge.name = form.name.data
        badge.description = form.description.data
        badge.icon = form.icon.data
        badge.color = form.color.data
        db.session.commit()
        return redirect(url_for("admin.all_badges"))

    form.name.process_data(badge.name)
    form.description.process_data(badge.description)
    form.icon.process_data(badge.icon)
    form.color.process_data(badge.color)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit Badge {badge.name} - Chop Shop Sign In")
