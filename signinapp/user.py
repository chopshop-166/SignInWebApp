from flask import Blueprint, Flask, redirect, url_for, flash
from flask.templating import render_template
from flask_login import current_user, login_required
from sqlalchemy.future import select

from .model import EventType, User, db

user = Blueprint("user", __name__)


@user.route("/profile/")
@login_required
def profile_self():
    return redirect(url_for("user.profile", username=current_user.username))


@user.route("/profile/<username>")
@login_required
def profile(username):
    user = db.session.scalar(select(User).filter_by(username=username))
    if not user:
        flash("Invalid user for profile")
        return redirect(url_for("index"))
    if not current_user.can_view(user):
        flash(f"No acces to view user data for {user.name}")
        return redirect(url_for("index"))
    event_types = db.session.scalars(select(EventType))
    return render_template("profile.html.jinja2", user=user, event_types=event_types)


def init_app(app: Flask):
    app.register_blueprint(user)
