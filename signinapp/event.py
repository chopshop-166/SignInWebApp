from http import HTTPStatus

import flask_excel as excel
from flask import (
    Blueprint,
    Flask,
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
@login_required
def event():
    if not current_user.role.can_display:
        flash("You don't have permissions to view the event scan page")
        return redirect(url_for("index"))
    event_code = request.values.get("event_code")
    if not event_code or not Event.get_from_code(event_code):
        flash("Invalid event code")
        return redirect(url_for("index"))
    return render_template(
        "event.html.jinja2", url_base=request.host_url, event_code=event_code
    )


@eventbp.route("/event/self")
@login_required
def selfevent():
    event_code = request.values.get("event_code")

    if not event_code or not (ev := Event.get_from_code(event_code)):
        flash("Invalid event code")
        return redirect(url_for("index"))

    if not ev.is_active:
        flash("Event is not active")
        return redirect(url_for("index"))

    if not current_user.is_signed_into(ev):
        ev.sign_in(current_user)

    return render_template("selfscan.html.jinja2", event=ev, event_code=ev.code)


@eventbp.route("/event/self/out")
@login_required
def selfout():
    event_code = request.values.get("event_code")

    if not event_code or not (ev := Event.get_from_code(event_code)):
        flash("Invalid event code")
        return redirect(url_for("index"))

    if not ev.is_active:
        flash("Event is not active")
        return redirect(url_for("index"))

    if current_user.is_signed_into(ev):
        active: Active = db.session.scalar(
            select(Active).filter_by(user=current_user, event=ev)
        )
        active.convert_to_stamp()

    return redirect(url_for("index"))


@eventbp.route("/scan", methods=["POST"])
def scan():
    event = request.values.get("event_code")
    user_code = request.values.get("user_code")

    if not user_code:
        return Response(
            f"Error: Not a valid QR code: {user_code}", HTTPStatus.BAD_REQUEST
        )
    if not (user := User.from_code(user_code)):
        return Response("Error: User does not exist", HTTPStatus.BAD_REQUEST)

    if not user.approved:
        return Response("Error: User is not approved", HTTPStatus.BAD_REQUEST)

    ev: Event = Event.get_from_code(event)

    if not ev:
        return Response("Error: Invalid event code")

    if not ev.is_active:
        return jsonify({"action": "redirect"})

    stamp = ev.scan(user)

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
    event = request.values.get("event", None)

    ev: Event = Event.get_from_code(event)

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
        name = request.values.get("name", None)
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


def init_app(app: Flask):
    app.register_blueprint(eventbp)
