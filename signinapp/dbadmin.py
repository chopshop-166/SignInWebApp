from flask import redirect, request, url_for, abort
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
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


def init_dbadmin(app):

    app.config["FLASK_ADMIN_SWATCH"] = "cyborg"
    flask_admin = Admin(
        index_view=AdminView(name="Home", url="/dbadmin", endpoint="dbadmin"),
        endpoint="dbadmin",
    )

    flask_admin.add_views(
        AuthModelView(Badge, db.session, endpoint="badge"),
        AuthModelView(Event, db.session, endpoint="adminevent"),
        AuthModelView(EventType, db.session, endpoint="eventtype"),
        AuthModelView(Guardian, db.session, endpoint="guardian"),
        AuthModelView(Role, db.session, endpoint="role"),
        AuthModelView(Student, db.session, endpoint="student"),
        AuthModelView(Subteam, db.session, endpoint="subteam"),
        AuthModelView(User, db.session, endpoint="adminuser"),
        AuthModelView(Stamps, db.session, endpoint="stamps"),
    )

    flask_admin.init_app(app)