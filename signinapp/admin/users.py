from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import FormField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo

from ..forms import GuardianDataForm, StudentDataForm, UserForm
from ..model import Pronoun, Role, ShirtSizes, User, db
from ..util import admin_required
from .util import admin


class EditGuardianDataForm(FlaskForm):
    guardian_data: GuardianDataForm = FormField(GuardianDataForm)
    submit = SubmitField()


class EditStudentDataForm(FlaskForm):
    student_data: StudentDataForm = FormField(StudentDataForm)
    submit = SubmitField()


class DeleteUserForm(FlaskForm):
    name = StringField(validators=[DataRequired()], render_kw={"readonly": True})
    verify = StringField(
        "Confirm Name",
        validators=[DataRequired(), EqualTo("name", message="Enter the user's name")],
    )
    submit = SubmitField()


@admin.route("/admin/users/approve", methods=["POST"])
@admin_required
def user_approve():
    user_id = request.args.get("user_id", None)
    user = db.session.get(User, user_id)
    if user:
        user.approved = True
        db.session.commit()
    else:
        flash("Invalid user ID")
    return redirect(url_for("team.users"))


@admin.route("/admin/guardian/promote", methods=["GET", "POST"])
@admin_required
def user_promote():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.list_guardians"))

    form = UserForm(obj=user)
    form.password.validators = [DataRequired()]
    del form.admin_data
    del form.student_data
    del form.subteam

    if form.validate_on_submit():
        if User.from_email(form.email.data) not in (None, user):
            flash(f"Username {form.email.data} already exists")
            return redirect(
                url_for("admin.user_promote", user_id=request.args["user_id"])
            )

        # Cannot use form.populate_data because of the password
        user.email = form.email.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role = Role.from_name("guardian")
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.address = form.address.data
        user.tshirt_size = ShirtSizes[form.tshirt_size.data]
        user.approved = True
        db.session.commit()
        return redirect(url_for("team.users"))

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Promote Guardian {user.name}",
    )


@admin.route("/admin/users/edit", methods=["GET", "POST"])
@admin_required
def edit_user():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    form = UserForm(obj=user)
    del form.student_data

    if form.validate_on_submit():
        if User.from_email(form.email.data) not in (None, user):
            flash(f"Username {form.email.data} already exists")
            return redirect(url_for("admin.edit_user", user_id=request.args["user_id"]))

        # Cannot use form.populate_data because of the password
        user.email = form.email.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role_id = form.admin_data.role.data
        user.subteam_id = form.subteam.data or None
        user.approved = form.admin_data.approved.data
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.address = form.address.data
        user.tshirt_size = ShirtSizes[form.tshirt_size.data]
        user.pronouns = Pronoun[form.pronouns.data]
        db.session.commit()
        return redirect(url_for("team.users"))

    form.phone_number.process_data(user.formatted_phone_number)

    form.admin_data.role.process_data(user.role_id)
    form.admin_data.approved.process_data(user.approved)
    form.subteam.process_data(user.subteam_id)
    form.tshirt_size.process_data(
        user.tshirt_size.value if user.tshirt_size else "Large"
    )
    form.pronouns.process_data(user.pronouns.value if user.pronounts else "He/Him")
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit User {user.name}",
    )


@admin.route("/admin/users/edit/student", methods=["GET", "POST"])
@admin_required
def edit_student_data():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.list_students"))

    form = EditStudentDataForm(obj=user)

    if form.validate_on_submit():
        student_data = user.student_user_data
        student_data.graduation_year = form.student_data.graduation_year.data
        student_data.update_guardians(form.student_data.guardian)
        db.session.commit()
        return redirect(url_for("team.users"))

    nested = form.student_data
    nested.graduation_year.process_data(user.student_user_data.graduation_year)
    for g in user.student_user_data.guardians:
        g.user.phone_number = g.user.formatted_phone_number
        nested.guardian.append_entry(g.user)
    nested.guardian.append_entry()

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Student Data {user.name}",
    )


@admin.route("/admin/users/edit/guardian", methods=["GET", "POST"])
@admin_required
def edit_guardian_data():
    user: User = db.session.get(User, request.args["user_id"])
    if not user or not user.role.guardian:
        flash("Invalid guardian user ID")
        return redirect(url_for("team.list_guardians"))

    form = EditGuardianDataForm(obj=user)

    if form.validate_on_submit():
        user.guardian_user_data.students = [
            db.session.get(User, s).student_user_data
            for s in form.guardian_data.data["student"]
            if s and s != "0"
        ]

        db.session.commit()
        return redirect(url_for("team.list_guardians"))

    nested = form.guardian_data.form
    nested.contact_order.process_data(user.guardian_user_data.contact_order)
    for s in user.guardian_user_data.students:
        nested.student.append_entry(s.user.id)
    # One more entry in case we're adding students
    nested.student.append_entry()

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Guardian Data {user.name}",
    )


@admin.route("/admin/users/delete", methods=["GET", "POST"])
@admin_required
def delete_user():
    user = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    form = DeleteUserForm(obj=user)
    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("team.users"))

    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Delete User {user.name}",
    )
