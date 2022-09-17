from flask import Blueprint, current_app, redirect, request, url_for
from flask.templating import render_template
from flask_login import current_user, login_required

from sqlalchemy.future import select

from .model import Badge, BadgeAward, EventType, User, db

user = Blueprint("user", __name__)


@user.route("/profile")
@login_required
def profile():
    user = current_user
    if uid := request.args.get("user_id"):
        user = db.session.get(User, uid)
    if current_user.can_view(user):
        event_types = db.session.scalars(select(EventType))
        return render_template("profile.html.jinja2", user=user, event_types=event_types)
    return current_app.login_manager.unauthorized()


@user.route("/badge")
@login_required
def badge():
    if bid := request.args.get("badge_id"):
        bid = int(bid)
        badge: Badge = db.session.get(Badge, bid)
        awards = sorted([a for a in badge.awards], key=lambda u: u.owner.name)
        return render_template("badge.html.jinja2", badge=badge, awards=awards)
    return redirect(url_for('mentor.all_badges', badge_id=badge.id))
