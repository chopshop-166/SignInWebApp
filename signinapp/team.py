from flask import Blueprint, request
from flask.templating import render_template
from flask_login import current_user, login_required

from .model import Role, Subteam, User

team = Blueprint("team", __name__)


@team.route("/admin/users")
@login_required
def users():
    users = User.query.all()
    roles = Role.query.all()
    return render_template("users.html.jinja2", users=users, roles=roles)


@team.route("/subteam")
@login_required
def subteam():
    st_id = request.args.get("st_id")
    subteam = Subteam.query.get(st_id)
    return render_template("subteam.html.jinja2", subteam=subteam)
