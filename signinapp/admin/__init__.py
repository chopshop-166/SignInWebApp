from flask import Flask, redirect, url_for
from flask.templating import render_template
from sqlalchemy import delete

from ..model import Active, db
from ..roles import rbac
from . import role, subteam, users  # noqa
from .util import admin


@admin.route("/admin/active/delete_all")
@rbac.allow(["admin"], methods=["GET"])
def active_deleteall():
    db.session.execute(delete(Active))
    db.session.commit()
    return redirect(url_for("mentor.active"))


@admin.route("/admin")
@rbac.allow(["admin"], methods=["GET"])
def admin_main():
    return render_template("admin/main.html.jinja2")


def init_app(app: Flask):
    app.register_blueprint(admin)
