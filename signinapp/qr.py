from flask import Blueprint, current_app, redirect, request, url_for
from flask.templating import render_template
from sqlalchemy.future import select
from flask import request

qr = Blueprint("qr", __name__)


@qr.route("/register/qr")
def register_qr():
    url = request.host_url
    return render_template("qr.html.jinja2", register_url=f"{url}register")
