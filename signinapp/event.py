from http import HTTPStatus

import flask_excel as excel
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask.templating import render_template
from flask_login import current_user, login_required
from sqlalchemy.future import select

from .model import Active, Event, EventType, Stamps, User, db

eventbp = Blueprint("event", __name__)


@eventbp.route("/event")
def event():
    event_code = request.args.get("event_code")
    if not event_code or not Event.get_from_code(event_code):
        flash("Invalid event code")
        return redirect(url_for("index"))
    return render_template("scan.html.jinja2", event_code=event_code)


@eventbp.route("/scan/self")
def selfscan():
    event_code = request.values["event_code"]

    ev: Event = db.session.scalar(
        select(Event).filter_by(code=event_code, enabled=True)
    )

    if not ev.is_active:
        return jsonify({"action": "redirect"})

    ev.scan(current_user.code)
    return redirect(url_for("event.event", event_code=event_code))


@eventbp.route("/scan", methods=["POST"])
def scan():
    event = request.values["event_code"]
    user_code = request.values["user_code"]

    ev: Event = db.session.scalar(select(Event).filter_by(code=event, enabled=True))

    if not ev:
        return Response("Error: Invalid event code")

    if not ev.is_active:
        return jsonify({"action": "redirect"})

    stamp = ev.scan(user_code)

    if isinstance(stamp, Response):
        print(stamp)
        return stamp
    else:
        return jsonify(
            {
                "message": f"{stamp.name} signed {stamp.event}",
                "users": Active.get(event),
                "action": "update",
            }
        )


@eventbp.route("/autoevent")
def autoevent():
    ev: Event = db.session.scalar(
        select(Event).filter_by(is_active=True).join(EventType).filter_by(autoload=True)
    )

    return jsonify({"event": ev.code if ev else ""})


@eventbp.route("/active")
def active():
    event = request.args.get("event", None)

    ev: Event = db.session.scalar(select(Event).filter_by(code=event, enabled=True))

    if ev and not ev.is_active:
        return jsonify({"action": "redirect"})

    return jsonify(
        {
            "users": Active.get(event),
            "action": "update",
            "message": "Updated user data",
        }
    )


@eventbp.route("/export")
@login_required
def export():
    if current_user.role.admin:
        name = request.args.get("name", None)
    else:
        name = current_user.name
    user = User.from_username(name)
    start = request.args.get("start", None)
    end = request.args.get("end", None)
    type_ = request.args.get("type", None)
    return excel.make_response_from_array(Stamps.export(user, start, end, type_), "csv")


@eventbp.route("/export/subteam")
@login_required
def export_subteam():
    if not current_user.can_see_subteam or not current_user.subteam_id:
        return current_app.login_manager.unauthorized()

    subteam = current_user.subteam
    return excel.make_response_from_array(Stamps.export(subteam=subteam), "csv")
