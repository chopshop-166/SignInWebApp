from flask import abort, redirect, request, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.theme import Bootstrap4Theme
from flask_login import current_user

from .model import (
    Badge,
    Event,
    EventType,
    Guardian,
    Role,
    Stamps,
    Student,
    Subteam,
    User,
    db,
)


class AuthModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role.admin

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for("auth.login", next=request.url))


class AdminView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role.admin

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        elif not current_user.role.admin:
            return abort(401)


def init_app(app):
    flask_admin = Admin(
        index_view=AdminView(name="Home", url="/dbadmin", endpoint="dbadmin"),
        endpoint="dbadmin",
        theme=Bootstrap4Theme(swatch="cyborg"),
    )

    with app.app_context():
        flask_admin.add_views(
            AuthModelView(Badge, db, endpoint="admin_badge"),
            AuthModelView(Event, db, endpoint="admin_event"),
            AuthModelView(EventType, db, endpoint="admin_eventtype"),
            AuthModelView(Guardian, db, endpoint="admin_guardian"),
            AuthModelView(Role, db, endpoint="admin_role"),
            AuthModelView(Student, db, endpoint="admin_student"),
            AuthModelView(Subteam, db, endpoint="admin_subteam"),
            AuthModelView(User, db, endpoint="admin_user"),
            AuthModelView(Stamps, db, endpoint="admin_stamps"),
        )

    flask_admin.init_app(app)
