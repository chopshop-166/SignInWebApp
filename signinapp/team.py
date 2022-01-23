#!/usr/bin/env python


from flask import (Blueprint, request, url_for)
from flask.templating import render_template
from flask_login import login_required

from .model import Subteam

team = Blueprint("team", __name__)

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']


@team.route("/subteam")
@login_required
def subteam():
    st_id = request.args.get("st_id")
    subteam = Subteam.query.get(st_id)
    return render_template("subteam.html.jinja2", subteam=subteam)
