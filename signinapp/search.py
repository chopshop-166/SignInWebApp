from flask import Blueprint
from flask.templating import render_template
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, EqualTo

from .model import Badge, BadgeAward, Subteam, User

search = Blueprint("search", __name__)


class BadgeSearchForm(FlaskForm):
    badge = SelectField()
    subteam = SelectField()
    required = BooleanField()
    submit = SubmitField()


@search.route("/search/badges", methods=["GET", "POST"])
@login_required
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
        return render_template("searchform.html.jinja2",
                               form=form, results=results)
    return render_template("searchform.html.jinja2", form=form, results=None)
