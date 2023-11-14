from flask import Blueprint, Flask, current_app, request, Response
from flask_login import current_user, login_required
import requests

bp = Blueprint("kanboard", __name__, url_prefix="/kanboard")


def calculate_headers(headers: dict):
    new_headers = dict()
    for header_name in [
        "cookie",
        "X-Requested-With",
    ]:
        if header_name in headers:
            new_headers[header_name] = headers[header_name]
    new_headers.update(
        {
            "REMOTE-USER": current_user.email,
            "REMOTE-EMAIL": current_user.email,
            "REMOTE-NAME": current_user.preferred_name,
        }
    )
    return new_headers


@bp.route("/<path:path>", methods=["GET", "POST"])
@bp.route("/", methods=["GET", "POST"])
@login_required
def index(path=""):
    url = current_app.config.get("PROXY_URL") + path
    headers = calculate_headers(request.headers)

    if request.method == "GET":
        resp = requests.get(url, params=dict(request.args), headers=headers)
    elif request.method == "POST":
        # If the content type isn't form-data then copy from data
        # Need to use find here since the content type looks like:
        # 'multipart/form-data; boundary=---------------------------5113784293436132453515092771'
        if not request.content_type.startswith(
            "multipart/form-data"
        ) and not request.content_type.startswith("application/x-www-form-urlencoded"):
            data = request.data
            headers["Content-Type"] = request.content_type
        else:
            data = request.form
        resp = requests.post(
            url,
            data=data,
            params=dict(request.args),
            headers=headers,
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
