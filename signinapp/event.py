from http import HTTPStatus

import flask_excel as excel
from flask import Blueprint, Response, current_app, jsonify, request
from flask.templating import render_template
from flask_login import current_user, login_required

from .model import Active, Event, EventType, Stamps

eventbp = Blueprint("event", __name__)


@eventbp.route("/event")
def event():
    event_code = request.args.get("event_code")
    if not event_code:
        return Response("Error: Invalid Event Code", HTTPStatus.BAD_REQUEST)
    return render_template("event.html.jinja2", event_code=event_code)


@eventbp.route("/scan", methods=['POST'])
def scan():
    event = request.values['event']
    name = request.values['name']

    ev: Event = Event.query.filter_by(code=event, enabled=True).one_or_none()

    if not ev.is_active:
        return jsonify({"action": "redirect"})

    stamp = ev.scan(name)

    if stamp:
        return jsonify({
            'message': f"{stamp.name} signed {stamp.event}",
            'users': Active.get(event),
            'action': 'update'
        })
    else:
        return Response("Error: Not a valid QR code", HTTPStatus.BAD_REQUEST)


@eventbp.route("/autoevent")
def autoevent():
    ev = Event.query.filter_by(is_active=True).join(
        EventType).filter_by(autoload=True).first()

    if ev:
        return jsonify({"event": ev.code})

    return jsonify({"event": ""})


@eventbp.route("/active")
def active():
    event = request.args.get("event", None)

    ev = Event.query.filter_by(code=event, enabled=True).one_or_none()

    if ev and not ev.is_active:
        return jsonify({"action": "redirect"})

    return jsonify({
        "users": Active.get(event),
        "action": "update",
        "message": "Updated user data"
    })


@eventbp.route("/export")
@login_required
def export():
    if current_user.role.admin:
        name = request.args.get("name", None)
    else:
        name = current_user.name
    start = request.args.get("start", None)
    end = request.args.get("end", None)
    type_ = request.args.get("type", None)
    return excel.make_response_from_array(Stamps.export(name, start, end, type_), "csv")


@eventbp.route("/export/subteam")
@login_required
def export_subteam():
    if not current_user.can_see_subteam or not current_user.subteam_id:
        return current_app.login_manager.unauthorized()

    subteam = current_user.subteam
    return excel.make_response_from_array(export(subteam=subteam), "csv")
