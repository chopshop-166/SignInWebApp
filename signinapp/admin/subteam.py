from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Subteam, db
from ..roles import rbac
from .util import admin


class SubteamForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    submit = SubmitField()


@admin.route("/admin/subteams", methods=["GET", "POST"])
@rbac.allow(["admin"], methods=["GET", "POST"])
def subteams():
    subteams = db.session.scalars(select(Subteam))
    return render_template("admin/subteams.html.jinja2", subteams=subteams)


@admin.route("/admin/subteams/new", methods=["GET", "POST"])
@rbac.allow(["admin"], methods=["GET", "POST"])
def new_subteam():
    form = SubteamForm()
    if form.validate_on_submit():
        st = Subteam(name=form.name.data)
        db.session.add(st)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template("form.html.jinja2", form=form, title="New Subteam")


@admin.route("/admin/subteams/edit", methods=["GET", "POST"])
@rbac.allow(["admin"], methods=["GET", "POST"])
def edit_subteam():
    st = db.session.get(Subteam, request.args["st_id"])
    if not st:
        flash("Invalid subteam ID")
        return redirect(url_for("admin.subteams"))

    form = SubteamForm(obj=st)
    if form.validate_on_submit():
        form.populate_obj(st)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Subteam {st.name}",
    )
