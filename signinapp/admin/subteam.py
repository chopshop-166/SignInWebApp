from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Subteam, db
from ..util import admin_required
from .util import admin


class SubteamForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    submit = SubmitField()


@admin.route("/admin/subteams", methods=["GET", "POST"])
@admin_required
def subteams():
    subteams = Subteam.query.all()
    return render_template("admin/subteams.html.jinja2", subteams=subteams)


@admin.route("/admin/subteams/new", methods=["GET", "POST"])
@admin_required
def new_subteam():
    form = SubteamForm()

    if form.validate_on_submit():
        st = Subteam(name=form.name.data)
        db.session.add(st)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template("admin/form.html.jinja2", form=form,
                           title=f"New Subteam - Chop Shop Sign In")


@admin.route("/admin/subteams/edit", methods=["GET", "POST"])
@admin_required
def edit_subteam():
    form = SubteamForm()
    st = Subteam.query.get(request.args["st_id"])

    if not st:
        flash("Invalid subteam ID")
        return redirect(url_for("admin.subteams"))

    if form.validate_on_submit():
        st.name = form.name.data
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    form.name.process_data(st.name)
    return render_template("admin/form.html.jinja2", form=form,
                           title=f"Edit Subteam {st.name} - Chop Shop Sign In")
