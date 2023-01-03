from flask import Blueprint, Flask, flash, redirect, request, url_for
from flask.templating import render_template
from sqlalchemy import delete
from sqlalchemy.future import select

from .model import Active, Stamps, db
from .util import admin_required, mentor_required

bp = Blueprint("active", __name__, url_prefix="/active")


@bp.route("/", methods=["GET"])
@mentor_required
def get():
    actives = db.session.scalars(select(Active))
    return render_template("active.html.jinja2", active=actives)


@bp.route("/", methods=["POST"])
@mentor_required
def post():
    active_event = db.session.get(Active, request.form["active_id"])
    stamp = Stamps(
        user=active_event.user, event=active_event.event, start=active_event.start
    )
    db.session.delete(active_event)
    db.session.add(stamp)
    db.session.commit()
    return redirect(url_for("mentor.active"))


@bp.route("/", methods=["DELETE"])
@mentor_required
def delete():
    # TODO: Check permissions
    active_event = db.session.get(Active, request.form["active_id"])
    db.session.delete(active_event)
    db.session.commit()
    return redirect(url_for("mentor.active"))


@bp.route("/delete_expired")
@mentor_required
def delete_expired():
    db.session.execute(
        delete(Active)
        .where(Active.event.has(is_active=False))
        .execution_options(synchronize_session="fetch"),
    )
    db.session.commit()
    flash("Deleted all expired stamps")
    return redirect(url_for("mentor.active"))


@bp.route("/delete_all")
@admin_required
def delete_all():
    db.session.execute(delete(Active))
    db.session.commit()
    return redirect(url_for("mentor.active"))


def init_app(app: Flask):
    app.register_blueprint(bp)
