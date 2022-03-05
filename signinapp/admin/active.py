from flask import redirect, request, url_for
from flask.templating import render_template
from sqlalchemy.sql.expression import not_

from ..model import Active, Event, Stamps, db
from ..util import admin_required
from .util import admin


@admin.route("/admin/active/delete_all")
@admin_required
def active_deleteall():
    Active.query.delete()
    db.session.commit()
    return redirect(url_for("mentor.active"))
