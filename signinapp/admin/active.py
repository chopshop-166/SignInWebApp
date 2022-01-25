from flask import redirect, request, url_for
from flask.templating import render_template

from ..model import Active, Stamps, db
from ..util import admin_required
from .util import admin


@admin.route("/admin/active", methods=["GET"])
@admin_required
def active():
    actives = Active.query.all()
    return render_template("admin/active.html.jinja2", active=actives)


@admin.route("/admin/active", methods=["POST"])
@admin_required
def active_post():
    active_event = Active.query.get(request.form["active_id"])
    stamp = Stamps(user=active_event.user,
                   event=active_event.event, start=active_event.start)
    db.session.delete(active_event)
    db.session.add(stamp)
    db.session.commit()
    return redirect(url_for("admin.active"))


@admin.route("/admin/active/delete", methods=["POST"])
@admin_required
def active_delete():
    active_event = Active.query.get(request.form["active_id"])
    db.session.delete(active_event)
    db.session.commit()
    return redirect(url_for("admin.active"))
