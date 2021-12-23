#!/usr/bin/env python

from flask import jsonify, request
from flask.templating import render_template

from . import app
from .models.dict_model import DictModel

model = DictModel()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan", methods=['POST'])
def scan():
    event = request.values['event']
    name = request.values['name']
    (human, sign) = model.scan(event, name)

    return jsonify({
        'stamp': sign,
        'message': f"{human} signed {sign}",
        'users': model.get(event)
    })


@app.route("/users")
def users_all():
    return jsonify(model.get_all())


@app.route("/users/<event>")
def users(event):
    return jsonify(model.get(event))
