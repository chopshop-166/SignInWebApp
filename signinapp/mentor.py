from flask import Blueprint, flash, redirect, request, url_for
from flask.templating import render_template
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import delete
from sqlalchemy.future import select
from wtforms import SubmitField

from .model import Active, Badge, Event, Stamps, User, db
from .util import MultiCheckboxField, mentor_required

mentor = Blueprint("mentor", __name__)


class BadgeAwardForm(FlaskForm):
    users = MultiCheckboxField()
    submit = SubmitField()


@mentor.route("/mentor/active", methods=["GET"])
@mentor_required
def active():
    actives = db.session.scalars(select(Active))
    return render_template("active.html.jinja2", active=actives)


@mentor.route("/mentor/active", methods=["POST"])
@mentor_required
def active_post():
    active_event = db.session.get(Active, request.form["active_id"])
    stamp = Stamps(
        user=active_event.user, event=active_event.event, start=active_event.start
    )
    db.session.delete(active_event)
    db.session.add(stamp)
    db.session.commit()
    return redirect(url_for("mentor.active"))


@mentor.route("/mentor/active/delete", methods=["POST"])
@mentor_required
def active_delete():
    active_event = db.session.get(Active, request.form["active_id"])
    db.session.delete(active_event)
    db.session.commit()
    return redirect(url_for("mentor.active"))


@mentor.route("/active/delete_expired")
@mentor_required
def active_delete_expired():
    db.session.execute(
        delete(Active)
        .where(Active.event.has(is_active=False))
        .execution_options(synchronize_session="fetch"),
    )
    db.session.commit()
    flash("Deleted all expired stamps")
    if current_user.role.admin:
        return redirect(url_for("mentor.active"))
    return redirect(url_for("mentor.active"))


@mentor.route("/badges", methods=["GET"])
@mentor_required
def all_badges():
    badges = db.session.scalars(select(Badge))
    return render_template("badges.html.jinja2", badges=badges)


@mentor.route("/badges/award", methods=["GET", "POST"])
@mentor_required
def award_badge():
    badge_id = int(request.args["badge_id"])

    people = db.session.scalars(select(User).filter_by(active=True))
    badge = db.session.get(Badge, badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("mentor.all_badges"))

    form = BadgeAwardForm()
    form.users.choices = [p.name for p in people]

    if form.validate_on_submit():
        for user in people:
            if user.name in form.users.data:
                user.award_badge(badge_id)
            else:
                user.remove_badge(badge_id)
        db.session.commit()
        return redirect(url_for("mentor.all_badges"))

    form.users.process_data([p.name for p in people if p.has_badge(badge_id)])

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Award Badge {badge.name}",
    )
