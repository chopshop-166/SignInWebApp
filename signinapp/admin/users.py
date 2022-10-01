from flask import flash, redirect, request, url_for
from flask.templating import render_template
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash
from wtforms import StringField, SubmitField, FormField
from wtforms.validators import DataRequired, EqualTo

from ..forms import StudentDataForm, UserForm
from ..model import Guardian, Role, ShirtSizes, Subteam, User, db, get_form_ids
from ..util import admin_required
from .util import admin


class EditStudentDataForm(FlaskForm):
    student_data = FormField(StudentDataForm)
    submit = SubmitField()


class DeleteUserForm(FlaskForm):
    name = StringField(validators=[DataRequired()])
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


@admin.route("/admin/guardian/promote", methods=["POST"])
@admin_required
def user_promote():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    form = UserForm(obj=user)
    form.password.flags.is_required = True
    del form.admin_data
    del form.student_data
    del form.subteam

    if form.validate_on_submit():
        # Cannot use form.populate_data because of the password
        user.username = form.username.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role = Role.from_name("guardian")
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.email = form.email.data
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


@admin.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = UserForm()
    form.admin_data.role.choices = get_form_ids(Role)
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)
    form.password.flags.is_required = True

    if form.validate_on_submit():
        if User.get_canonical(form.name.data) is not None:
            flash("User already exists")
            return redirect(url_for("admin.new_user"))

        user = User.make(
            username=form.username.data,
            name=form.name.data,
            password=form.password.data,
            approved=form.approved.data,
            role=db.session.get(Role, form.role.data),
            preferred_name=form.preferred_name.data,
            phone_number=form.phone_number.data,
            email=form.email.data,
            address=form.address.data,
            tshirt_size=ShirtSizes[form.tshirt_size.data],
        )
        if form.subteam.data:
            user.subteam = db.session.get(Subteam, form.subteam.data)

        db.session.add(user)
        db.session.commit()
        return redirect(url_for("team.users"))

    form.role.process_data(Role.get_default().id)

    return render_template("form.html.jinja2", form=form, title=f"New User")


@admin.route("/admin/users/edit", methods=["GET", "POST"])
@admin_required
def edit_user():
    user: User = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    form = UserForm(obj=user)
    form.admin_data.role.choices = get_form_ids(Role)
    form.subteam.choices = get_form_ids(Subteam, add_null_id=True)

    if user.role.name != "student":
        del form.student_data

    if form.validate_on_submit():
        # Cannot use form.populate_data because of the password
        user.username = form.username.data
        user.name = form.name.data
        if form.password.data:
            user.password = generate_password_hash(form.password.data)
        user.role_id = form.admin_data.role.data
        user.subteam_id = form.subteam.data or None
        user.approved = form.admin_data.approved.data
        user.preferred_name = form.preferred_name.data
        user.phone_number = form.phone_number.data
        user.email = form.email.data
        user.address = form.address.data
        user.tshirt_size = ShirtSizes[form.tshirt_size.data]
        db.session.commit()
        return redirect(url_for("team.users"))

    form.admin_data.role.process_data(user.role_id)
    form.admin_data.approved.process_data(user.approved)
    form.subteam.process_data(user.subteam_id)
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
        return redirect(url_for("team.users"))

    form = EditStudentDataForm(obj=user)

    if form.validate_on_submit():
        student_data = user.student_user_data
        student_data.graduation_year = form.student_data.graduation_year.data
        student_data.guardians.clear()
        student_data.guardians.append(
            Guardian.get_from(
                form.student_data.first_guardian_name.data,
                form.student_data.first_guardian_phone_number.data,
                form.student_data.first_guardian_email.data,
                1,
            )
        )
        if form.student_data.second_guardian_name.data:
            student_data.guardians.append(
                Guardian.get_from(
                    form.student_data.second_guardian_name.data,
                    form.student_data.second_guardian_phone_number.data,
                    form.student_data.second_guardian_email.data,
                    2,
                )
            )
        db.session.commit()
        return redirect(url_for("team.users"))

    nested = form.student_data
    nested.graduation_year.process_data(user.student_user_data.graduation_year)
    guardians = user.student_user_data.guardians
    first_guardian = guardians[0].user
    nested.first_guardian_name.process_data(first_guardian.name)
    nested.first_guardian_phone_number.process_data(first_guardian.phone_number)
    nested.first_guardian_email.process_data(first_guardian.email)
    if len(guardians) > 1:
        second_guardian = guardians[1].user
        nested.second_guardian_name.process_data(second_guardian.name)
        nested.second_guardian_phone_number.process_data(second_guardian.phone_number)
        nested.second_guardian_email.process_data(second_guardian.email)
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Edit Student Data {user.name}",
    )


@admin.route("/admin/users/delete", methods=["GET", "POST"])
@admin_required
def delete_user():
    form = DeleteUserForm()
    user = db.session.get(User, request.args["user_id"])
    if not user:
        flash("Invalid user ID")
        return redirect(url_for("team.users"))

    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("team.users"))

    form.name.process_data(user.name)
    return render_template(
        "form.html.jinja2",
        form=form,
        title=f"Delete User {user.name}",
    )
