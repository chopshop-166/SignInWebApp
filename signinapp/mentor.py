from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import not_, select
from wtforms import SubmitField

from .model import Active, Badge, Event, User, db
from .util import MultiCheckboxField, mentor_required

mentor = Blueprint("mentor", __name__)


class BadgeAwardForm(FlaskForm):
    users = MultiCheckboxField()
    submit = SubmitField()


@mentor.route("/active/delete_expired")
@mentor_required
def active_delete_expired():
    inactive_events = select(Event.id).where(not_(Event.is_active))
    q = Active.query.filter(Active.event_id.in_(inactive_events))
    q.delete(synchronize_session=False)
    db.session.commit()
    flash("Deleted all expired stamps")
    if current_user.role.admin:
        return redirect(url_for("admin.active"))
    return redirect(url_for("index"))


@mentor.route("/badges/award", methods=["GET", "POST"])
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
