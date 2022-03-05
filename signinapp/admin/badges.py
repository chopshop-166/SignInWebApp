from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, widgets
from wtforms.widgets import ColorInput
from wtforms.validators import DataRequired

from ..model import Badge, User, db
from ..util import admin_required, MultiCheckboxField
from .util import admin


class BadgeForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    icon = StringField()
    color = StringField("Icon Color", widget=ColorInput())
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
        badge = Badge()
        form.populate_obj(badge)
        db.session.add(badge)
        db.session.commit()
        return redirect(url_for("admin.all_badges"))

    return render_template("admin/form.html.jinja2", form=form,
                           title="New Badge - Chop Shop Sign In")


@admin.route("/admin/badges/edit", methods=["GET", "POST"])
@admin_required
def edit_badge():
    badge_id = request.args["badge_id"]
    badge = Badge.query.get(badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("admin.all_badges"))

    form = BadgeForm(obj=badge)

    if form.validate_on_submit():
        form.populate_obj(badge)
        db.session.commit()
        return redirect(url_for("admin.all_badges"))

    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit Badge {badge.name} - Chop Shop Sign In")
