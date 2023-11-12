from flask import Blueprint, Flask, current_app, request, Response
from flask_login import current_user, login_required
import requests

bp = Blueprint("kanboard", __name__, url_prefix="/kanboard")


def get_user_headers():
    return {
        "REMOTE-USER": current_user.email,
        "REMOTE-EMAIL": current_user.email,
        "REMOTE-NAME": current_user.preferred_name,
    }


@bp.route("/<path:path>", methods=["GET", "POST"])
@bp.route("/", methods=["GET", "POST"])
@login_required
def index(path=""):
    url = current_app.config.get("PROXY_URL") + path

    if request.method == "GET":
        resp = requests.get(url, headers=get_user_headers())
    elif request.method == "POST":
        resp = requests.post(
            url,
            data=request.form,
            headers=get_user_headers(),
        )
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    ]
    headers = [
        (name, value)
        for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers
    ]
    response = Response(resp.content, resp.status_code, headers)
    return response


def init_app(app: Flask):
    app.register_blueprint(bp)
