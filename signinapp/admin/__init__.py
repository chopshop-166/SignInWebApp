from flask import Flask, redirect, url_for
from flask.templating import render_template
from sqlalchemy import delete

from ..model import Active, db
from ..util import admin_required
from . import badges, role, subteam, users  # noqa
from .util import admin


@admin.route("/admin/active/delete_all")
@admin_required
def active_deleteall():
    db.session.execute(delete(Active))
    db.session.commit()
    return redirect(url_for("mentor.active"))


@admin.route("/admin")
@admin_required
def admin_main():
    return render_template("admin/main.html.jinja2")


def init_app(app: Flask):
    app.register_blueprint(admin)
