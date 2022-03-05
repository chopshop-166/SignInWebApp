from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, widgets
from wtforms.validators import DataRequired

from .model import Badge, User, db
from .util import mentor_required, MultiCheckboxField

mentor = Blueprint("mentor", __name__)


class BadgeAwardForm(FlaskForm):
    users = MultiCheckboxField()
    submit = SubmitField()


@mentor.route("/mentor/badges/award", methods=["GET", "POST"])
@mentor_required
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
