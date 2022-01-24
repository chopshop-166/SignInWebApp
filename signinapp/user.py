#!/usr/bin/env python

from http import HTTPStatus

from flask import (Blueprint, Response, current_app, flash, redirect, request,
                   url_for)
from flask.templating import render_template
from flask_login import current_user, login_required
from flask_login.config import EXEMPT_METHODS
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired

from .model import Badge, BadgeAward, EventType, User

user = Blueprint("user", __name__)

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']


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
