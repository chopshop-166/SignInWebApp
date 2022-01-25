#!/usr/bin/env python

from flask import Blueprint, current_app, request
from flask.templating import render_template
from flask_login import current_user, login_required

from .model import Badge, BadgeAward, EventType, User

user = Blueprint("user", __name__)


@user.route("/profile")
@login_required
def profile():
    user = current_user
    if uid := request.args.get("user_id"):
        user = User.query.get(uid)
    if current_user.can_view(user):
        event_types = EventType.query.all()
        return render_template("profile.html.jinja2", user=user, event_types=event_types)
    return current_app.login_manager.unauthorized()


@user.route("/badge")
@login_required
def badge():
    if bid := request.args.get("badge_id"):
        bid = int(bid)
        badge = Badge.query.get(bid)
        awards = BadgeAward.query.filter_by(badge_id=bid).all()
        awards.sort(key=lambda u: u.owner.name)
        return render_template("badge.html.jinja2", badge=badge, awards=awards)
    return current_app.login_manager.unauthorized()
