from flask import Blueprint, Flask
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField

from .model import Badge, EventType, Role, Subteam, User, db, get_form_ids
from .util import MultiCheckboxField, mentor_required

search = Blueprint("search", __name__)


class BadgeSearchForm(FlaskForm):
    badge = SelectField(choices=lambda: get_form_ids(Badge))
    subteam = SelectField(choices=lambda: get_form_ids(Subteam, add_null_id=True))
    required = BooleanField(label="Has Badge", default=True)
    submit = SubmitField()


class HoursForm(FlaskForm):
    role = MultiCheckboxField()
    category = SelectField(choices=lambda: get_form_ids(EventType))
    submit = SubmitField()


@search.route("/badges/search", methods=["GET", "POST"])
@mentor_required
def badges():
    form = BadgeSearchForm()

    if form.validate_on_submit():
        users = User.get_visible_users()
        if int(form.subteam.data) != 0:
            subteam = db.session.get(Subteam, form.subteam.data)
            users = [u for u in users if u.subteam == subteam]
        badge = db.session.get(Badge, form.badge.data)
        if form.required.data:
            results = [u for u in users if badge in u.badges]
        else:
            results = [u for u in users if badge not in u.badges]
        return render_template("search/badges.html.jinja2", form=form, results=results)
    return render_template("search/badges.html.jinja2", form=form, results=None)


@search.route("/search/hours", methods=["GET", "POST"])
@mentor_required
def hours():
    form = HoursForm()
    form.role.choices = [r.name for r in Role.get_visible()]

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
