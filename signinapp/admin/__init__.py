from flask.templating import render_template

from .active import *
from .badges import *
from .events import *
from .role import *
from .subteam import *
from .users import *
from .util import *


@admin.route("/admin")
@admin_required
def admin_main():
    return render_template("admin/main.html.jinja2")
