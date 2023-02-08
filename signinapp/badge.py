from flask import Blueprint, Flask, flash, redirect, request, url_for
from flask.templating import render_template
from flask_login import login_required
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired
from wtforms.widgets import ColorInput

from .model import Badge, BadgeAward, Subteam, User, db, get_form_ids
from .util import MultiCheckboxField, admin_required, mentor_required

bp = Blueprint("badge", __name__, url_prefix="/badge")


class BadgeForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    description = StringField()
    emoji = StringField()
    icon = StringField()
    color = StringField("Icon Color", widget=ColorInput())
    submit = SubmitField()


class BadgeAwardForm(FlaskForm):
    users = MultiCheckboxField()
    submit = SubmitField()


class BadgeSearchForm(FlaskForm):
    badge = SelectField(choices=lambda: get_form_ids(Badge))
    subteam = SelectField(choices=lambda: get_form_ids(Subteam, add_null_id=True))
    required = BooleanField(label="Has Badge", default=True)
    submit = SubmitField()


@bp.route("/view")
@login_required
def view():
    if bid := request.args.get("badge_id"):
        bid = int(bid)
        badge: Badge = db.session.get(Badge, bid)
        awards: list[BadgeAward] = sorted(
            [a for a in badge.awards], key=lambda u: u.owner.name
        )
        return render_template("badge.html.jinja2", badge=badge, awards=awards)
    return redirect(url_for("mentor.all_badges", badge_id=badge.id))


@bp.route("/", endpoint="all")
@mentor_required
def all_badges():
    badges = db.session.scalars(select(Badge))
    return render_template("badges.html.jinja2", badges=badges)


@bp.route("/award", methods=["GET", "POST"])
@mentor_required
def award():
    people: list[User] = User.get_visible_users()
    badge = db.session.get(Badge, request.args["badge_id"])

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("mentor.all_badges"))

    form = BadgeAwardForm()
    form.users.choices = [p.name for p in people]

    if form.validate_on_submit():
        for user in people:
            if user.name in form.users.data:
                user.award_badge(badge)
            else:
                user.remove_badge(badge)
        db.session.commit()
        return redirect(url_for("mentor.all_badges"))

    form.users.process_data([p.name for p in people if badge in p.badges])

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Award Badge {badge.name}",
    )


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new():
    form = BadgeForm()
    if form.validate_on_submit():
        badge = Badge()
        form.populate_obj(badge)
        db.session.add(badge)
        db.session.commit()
        return redirect(url_for("mentor.all_badges"))

    return render_template("form.html.jinja2", form=form, title="New Badge")


@bp.route("/edit", methods=["GET", "POST"])
@admin_required
def edit():
    badge_id = request.args["badge_id"]
    badge = db.session.get(Badge, badge_id)

    if not badge:
        flash("Badge does not exist")
        return redirect(url_for("mentor.all_badges"))

    form = BadgeForm(obj=badge)

    if form.validate_on_submit():
        form.populate_obj(badge)
        db.session.commit()
        return redirect(url_for("mentor.all_badges"))

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Badge {badge.name}",
    )


@bp.route("/search", methods=["GET", "POST"])
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


def init_app(app: Flask):
    app.register_blueprint(bp)
