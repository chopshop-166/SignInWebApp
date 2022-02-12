from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, widgets
from wtforms.validators import DataRequired

from ..model import Badge, User, db
from ..util import admin_required
from .util import admin


class BadgeForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    icon = StringField()
    color = StringField("Icon Color")
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


@admin.route("/admin/badges/award", methods=["GET", "POST"])
@admin_required
def award_badge():
    badge_id = int(request.args["badge_id"])

    people = User.query.filter_by(active=True).all()
    badge = Badge.query.get(badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("admin.all_badges"))
        
    form = BadgeAwardForm()
    form.users.choices = [p.name for p in people]

    if form.validate_on_submit():
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
