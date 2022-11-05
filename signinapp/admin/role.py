from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from sqlalchemy.future import select
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired

from ..model import Role, db
from ..util import admin_required
from .util import admin


class RoleForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
    admin = BooleanField()
    mentor = BooleanField()
    can_display = BooleanField("Can display event pages")
    autoload = BooleanField("Automatically load event pages")
    can_see_subteam = BooleanField("Can view subteam stamps")
    default_role = BooleanField("Is the default role for new accounts")
    submit = SubmitField()


@admin.route("/admin/roles", methods=["GET", "POST"])
@admin_required
def roles():
    roles = db.session.scalars(select(Role))
    return render_template("admin/roles.html.jinja2", roles=roles)


@admin.route("/admin/roles/new", methods=["GET", "POST"])
@admin_required
def new_role():
    form = RoleForm()
    if form.validate_on_submit():
        r = Role()
        form.populate_obj(r)
        if form.default_role.data:
            Role.set_default(r)
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template("form.html.jinja2", form=form, title="New Role")


@admin.route("/admin/roles/edit", methods=["GET", "POST"])
@admin_required
def edit_role():
    r = db.session.get(Role, request.args["role_id"])
    if not r:
        flash("Invalid role ID")
        return redirect(url_for("admin.roles"))

    form = RoleForm(obj=r)
    if form.validate_on_submit():
        form.populate_obj(r)
        if form.default_role.data:
            Role.set_default(r)
        db.session.commit()
        return redirect(url_for("admin.subteams"))

    return render_template("form.html.jinja2", form=form, title=f"Edit Role {r.name}")
