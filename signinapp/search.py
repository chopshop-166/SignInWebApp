from flask import Blueprint
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField

from .model import Badge, EventType, Role, Subteam, User
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
    form.badge.choices = [(b.id, b.name) for b in Badge.query.all()]
    form.subteam.choices = [(0, "None")]+[(s.id, s.name)
                                          for s in Subteam.query.all()]

    if form.validate_on_submit():
        query = User.query
        if int(form.subteam.data) != 0:
            query = query.filter_by(subteam_id=form.subteam.data)
        results : list[User] = query.all()
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
    form.role.choices = [r.name for r in Role.query.all()]
    form.category.choices = [(r.id, r.name) for r in EventType.query.all()]

    if form.validate_on_submit():
        results = User.query.all()
        event_type = EventType.query.get(form.category.data)
        roles = [Role.from_name(r).id for r in form.role.data]
        results = [(u.name, u.total_stamps_for(event_type))
                   for u in results if u.role_id in roles]
        return render_template("search/hours.html.jinja2",
                               form=form, results=results)

    return render_template("search/hours.html.jinja2", form=form, results=None)
