from collections import defaultdict

from flask import Blueprint, Flask, request
from flask.templating import render_template
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.future import select

from .model import Role, ShirtSizes, Subteam, User, db
from .roles import rbac

team = Blueprint("team", __name__)


@team.route("/users")
@rbac.allow(["mentor"], methods=["GET"])
def users():
    users = User.get_visible_users()
    roles = db.session.scalars(select(Role))
    return render_template("users.html.jinja2", users=users, roles=roles)


@team.route("/shirts")
@rbac.allow(["mentor"], methods=["GET"])
def shirts():
    shirts = defaultdict(lambda: defaultdict(lambda: 0))
    for size in ShirtSizes:
        shirts[size]
    for u in User.get_visible_users():
        if u.tshirt_size:
            shirts[u.tshirt_size][u.role] += 1
    return render_template("shirts.html.jinja2", shirts=shirts)


@team.route("/subteam")
@login_required
def subteam():
    st_id = request.args.get("st_id")
    subteam = db.session.get(Subteam, st_id)
    return render_template("subteam.html.jinja2", subteam=subteam)


@team.route("/users/students")
@rbac.allow(["mentor"], methods=["GET"])
def list_students():
    users = User.get_by_role("student")
    return render_template("user_list.html.jinja2", role="Student", users=users)


@team.route("/users/guardians")
@rbac.allow(["mentor"], methods=["GET"])
def list_guardians():
    users = User.get_by_role("guardian_limited")
    return render_template("user_list.html.jinja2", role="Guardian", users=users)


@team.route("/users/mentors")
@rbac.allow(["mentor"], methods=["GET"])
def list_mentors():
    users = User.get_by_role("mentor")
    return render_template("user_list.html.jinja2", role="Mentor", users=users)


def init_app(app: Flask):
    app.register_blueprint(team)
