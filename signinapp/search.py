from flask import Blueprint
from flask.templating import render_template
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from wtforms import BooleanField, SelectField, SubmitField

from .model import Badge, EventType, Role, Subteam, User, db, get_form_ids
from .util import MultiCheckboxField, mentor_required

search = Blueprint("search", __name__)


class BadgeSearchForm(FlaskForm):
    badge = SelectField()
    subteam = SelectField()
    required = BooleanField(label="Has Badge", default=True)
    submit = SubmitField()


class HoursForm(FlaskForm):
    role = MultiCheckboxField()
    category = SelectField()
    submit = SubmitField()


@search.route("/search/badges", methods=["GET", "POST"])
@mentor_required
def badges():
    form = BadgeSearchForm()
    form.badge.choices = get_form_ids(Badge)
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)

    if form.validate_on_submit():
        stmt = select(User)
        if int(form.subteam.data) != 0:
            stmt = stmt.filter_by(subteam_id=form.subteam.data)
        results = db.session.scalars(stmt)
        if form.required.data:
            results = [u for u in results
                       if u.has_badge(int(form.badge.data))]
        else:
            results = [u for u in results
                       if not u.has_badge(int(form.badge.data))]
        return render_template("search/badges.html.jinja2",
                               form=form, results=results)
    return render_template("search/badges.html.jinja2", form=form, results=None)


@search.route("/search/hours", methods=["GET", "POST"])
@mentor_required
def hours():
    form = HoursForm()
    form.role.choices = [r.name for r in Role.get_visible()]
    form.category.choices = get_form_ids(EventType)

    if form.validate_on_submit():
        results = User.get_visible_users()
        event_type = db.session.get(EventType, form.category.data)
        roles = [Role.from_name(r).id for r in form.role.data]
        results = [(u.name, u.total_stamps_for(event_type))
                   for u in results if u.role_id in roles]
        return render_template("search/hours.html.jinja2",
                               form=form, results=results)

    return render_template("search/hours.html.jinja2", form=form, results=None)
