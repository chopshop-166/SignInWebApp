import locale

from flask import Blueprint, Flask, render_template
from sqlalchemy.future import select

from .model import Event, Role, User, db
from .util import admin_required

finance = Blueprint("finance", __name__)


@finance.route("/finance")
@admin_required
def overview():
    all_events: list[Event] = db.session.scalars(select(Event))
    all_users: list[User] = db.session.scalars(
        select(User).join(Role).where(Role.visible == True, Role.receives_funds == True)
    )
    total_overhead = (
        sum(((ev.funds - ev.cost) * ev.overhead) for ev in all_events) / 100.0
    )
    user_funds = sorted([(u.display_name, u.yearly_funds()) for u in all_users])
    return render_template(
        "finance.html.jinja2", total_overhead=total_overhead, user_funds=user_funds
    )


def init_app(app: Flask):
    app.register_blueprint(finance)
