#!/usr/bin/env python

from http import HTTPStatus
from flask import Blueprint, flash, redirect, url_for, Response, request, abort
from flask.templating import render_template
from flask_login import LoginManager, current_user, login_required
from werkzeug.security import check_password_hash

from .model import db
from .model import Person, Role

login_manager = LoginManager()

admin = Blueprint("admin", __name__)


@admin.route("/admin/users", methods=["GET", "POST"])
@login_required
def admin_users():
    if current_user.admin:
        users = Person.query.all()
        roles = Role.query.all()
        return render_template("admin_user.html", users=users, roles=roles)
    return Response("You're not admin", HTTPStatus.FORBIDDEN)

@admin.route("/admin/users/update_role", methods=["POST"])
@login_required
def update_role():
    if not current_user.admin:
        return Response("You're not admin", HTTPStatus.FORBIDDEN)
        
    if user := Person.query.get(int(request.form["user_id"])):
        if role := Role.query.get(int(request.form["role"])):
            user.role_id = role.id
            db.session.commit()
            print("Role for", user.name, "is", user.role_id, "should be", role.id)
            return redirect(url_for("admin.admin_users"))
        flash("Invalid role ID")
        return Response("Invalid role ID", HTTPStatus.BAD_REQUEST)
    flash("Invalid user ID")
    return Response("Invalid user ID", HTTPStatus.BAD_REQUEST)