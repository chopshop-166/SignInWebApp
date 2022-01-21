#!/usr/bin/env python

from http import HTTPStatus

import flask_excel as excel
from flask import Blueprint, Response, jsonify, request
from flask.templating import render_template

from .model import model

qrbp = Blueprint("qr", __name__)


@qrbp.route("/")
def index():
    return render_template("index.html")


@qrbp.route("/scan", methods=['POST'])
def scan():
    event = request.values['event']
    name = request.values['name']
    stamp = model.scan(event, name)

    if stamp:
        return jsonify({
            'stamp': stamp.event,
            'message': f"{stamp.name} signed {stamp.event}",
            'users': model.get_active(event)
        })
    else:
        return Response("Error: Not a valid QR code", HTTPStatus.BAD_REQUEST)


@qrbp.route("/active")
def active():
    event = request.args.get("event", None)
    return jsonify(model.get_active(event))


@qrbp.route("/stamps")
def stamps():
    name = request.args.get("name", None)
    event = request.args.get("event", None)
    return jsonify(model.get_stamps(name=name, event=event))


@qrbp.route("/export")
def export():
    name = request.args.get("name", None)
    start = request.args.get("start", None)
    end = request.args.get("end", None)
    type_ = request.args.get("type", None)
    return excel.make_response_from_array(
        model.export(name, start, end, type_), "csv")