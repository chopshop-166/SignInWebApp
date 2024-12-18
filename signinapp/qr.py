from flask import Blueprint, Flask, request, url_for
from flask.templating import render_template

qr = Blueprint("qr", __name__)


@qr.route("/register/qr")
def register_qr():
    url = request.host_url
    return render_template("qr.html.jinja2", register_url=f"{url}{url_for('auth.register')}")


@qr.route("/register/mentor/qr")
def register_mentor_qr():
    url = request.host_url
    return render_template("qr.html.jinja2", register_url=f"{url}{url_for('auth.register_mentor')}")


@qr.route("/register/guardian/qr")
def register_guardian_qr():
    url = request.host_url
    return render_template(
        "qr.html.jinja2", register_url=f"{url}{url_for('auth.register_guardian')}"
    )


def init_app(app: Flask):
    app.register_blueprint(qr)
