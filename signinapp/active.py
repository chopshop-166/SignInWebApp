from flask import Blueprint, Flask, flash, redirect, request, url_for
from flask.templating import render_template
from sqlalchemy import delete
from sqlalchemy.future import select

from .model import Active, Stamps, db
from .roles import rbac

bp = Blueprint("active", __name__, url_prefix="/active")


@bp.route("/", methods=["GET"])
@rbac.allow(["mentor"], methods=["GET"])
def get():
    actives = db.session.scalars(select(Active))
    return render_template("active.html.jinja2", active=actives)


@bp.route("/", methods=["DELETE"], endpoint="delete")
@rbac.allow(["mentor"], methods=["DELETE"])
def delete_one():
    # TODO: Check permissions
    active_event = db.session.get(Active, request.form["active_id"])
    db.session.delete(active_event)
    db.session.commit()
    return redirect(url_for("active.get"))


@bp.route("/delete_expired")
@rbac.allow(["mentor"], methods=["DELETE"])
def delete_expired():
    db.session.execute(
        delete(Active)
        .where(Active.event.has(is_active=False))
        .execution_options(synchronize_session="fetch"),
    )
    db.session.commit()
    flash("Deleted all expired stamps")
    return redirect(url_for("active.get"))


@bp.route("/delete_all")
@rbac.allow(["admin"], methods=["GET"])
def delete_all():
    db.session.execute(delete(Active))
    db.session.commit()
    return redirect(url_for("active.get"))


def init_app(app: Flask):
    app.register_blueprint(bp)
