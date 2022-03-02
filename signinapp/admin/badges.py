from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, widgets
from wtforms.widgets import ColorInput
from wtforms.validators import DataRequired

from ..model import Badge, User, db
from ..util import admin_required
from .util import admin


class BadgeForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    icon = StringField()
    color = StringField("Icon Color", widget=ColorInput())
    submit = SubmitField()


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class BadgeAwardForm(FlaskForm):
    users = MultiCheckboxField()
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


@admin.route("/admin/badges/award", methods=["GET", "POST"])
@admin_required
def award_badge():
    badge_id = int(request.args["badge_id"])

    form = BadgeAwardForm()
    people = User.query.filter_by(active=True).all()
    form.users.choices = [p.name for p in people]
    badge = Badge.query.get(badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("admin.all_badges"))

    if form.validate_on_submit():
        print(form.users.data)
        for user in people:
            if user.name in form.users.data:
                user.award_badge(badge_id)
            else:
                user.remove_badge(badge_id)
        db.session.commit()
        return redirect(url_for("admin.all_badges"))

    form.users.process_data([p.name for p in people if p.has_badge(badge_id)])

    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Award Badge {badge.name} - Chop Shop Sign In")
