from flask import redirect, url_for
from sqlalchemy import delete

from ..model import Active, db
from ..util import admin_required
from .util import admin


@admin.route("/admin/active/delete_all")
@admin_required
def active_deleteall():
    db.session.execute(delete(Active))
    db.session.commit()
    return redirect(url_for("mentor.active"))
