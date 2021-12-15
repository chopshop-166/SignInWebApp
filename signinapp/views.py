#!/usr/bin/env python

from flask import Flask, jsonify
from flask.templating import render_template

from . import app
from .models.dict_model import DictModel

model = DictModel()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scan/<event>/<name>")
def scan(event, name):
    (human, sign) = model.scan(event, name)
    print(f"'{name}' signed {sign} to event '{event}'")

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
