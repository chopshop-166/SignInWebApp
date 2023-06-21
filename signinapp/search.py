from flask import Blueprint, Flask
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField

from .model import Badge, EventType, Role, Subteam, User, db, get_form_ids
from .roles import rbac
from .util import MultiCheckboxField

search = Blueprint("search", __name__)


class HoursForm(FlaskForm):
    role = MultiCheckboxField()
    category = SelectField(choices=lambda: get_form_ids(EventType))
    submit = SubmitField()


@search.route("/search/hours", methods=["GET", "POST"])
@rbac.allow(["mentor"], methods=["GET", "POST"])
def hours():
    form = HoursForm()
    form.role.choices = [r.name for r in Role.get_all()]

    if form.validate_on_submit():
        users = User.get_visible_users()
        event_type = db.session.get(EventType, form.category.data)
        roles = [Role.from_name(r).id for r in form.role.data]
        results = sorted(
            [
                (u.display_name, u.total_stamps_for(event_type))
                for u in users
                if u.role_id in roles and u.total_time and u.approved
            ]
        )
        return render_template("search/hours.html.jinja2", form=form, results=results)

    return render_template("search/hours.html.jinja2", form=form, results=None)


def init_app(app: Flask):
    app.register_blueprint(search)
