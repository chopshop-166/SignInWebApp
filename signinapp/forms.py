import regex

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    FieldList,
    Form,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
)
from wtforms.validators import DataRequired, Email, Optional, Regexp

from .model import Role, ShirtSizes, Subteam, User, generate_grade_choices, get_form_ids

NAME_RE = regex.compile(r"(\p{L}+(['\-]\p{L}+)*)( \p{L}+(['\-]\p{L}+)*)*")


def strip(s):
    return (s or "").strip()


class GuardianDataForm(Form):
    contact_order = IntegerField("Contact Order", default=1)
    student = FieldList(
        SelectField(
            "Student",
            choices=lambda: get_form_ids(
                User, add_null_id=True, filters=(User.role.has(name="student"),)
            ),
        )
    )


class GuardianInfoForm(Form):
    name = StringField(
        "Name",
        validators=[Optional(), Regexp(NAME_RE)],
        filters=[strip],
    )
    phone_number = TelField("Phone Number")
    email = EmailField("email", validators=[Optional(), Email()])


class StudentDataForm(Form):
    graduation_year = SelectField(
        "Graduation Year",
        validators=[DataRequired()],
        choices=lambda: generate_grade_choices().items(),
    )

    guardian = FieldList(FormField(GuardianInfoForm))


class AdminUserForm(Form):
    role = SelectField(choices=lambda: get_form_ids(Role))
    approved = BooleanField()


class UserForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Regexp(r"\w+")], filters=[strip]
    )
    password = PasswordField("Password")

    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Regexp(NAME_RE),
        ],
        filters=[strip],
    )
    preferred_name = StringField(
        "Preferred Name", description="Leave blank for none", filters=[strip]
    )

    phone_number = TelField("Phone Number", validators=[DataRequired()])
    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        description="Preferably a non-school address",
    )
    address = StringField("Street Address", validators=[DataRequired()])
    tshirt_size = SelectField(
        "T-Shirt Size", choices=ShirtSizes.get_size_names(), validators=[DataRequired()]
    )
    subteam = SelectField(
        "Subteam",
        validators=[DataRequired()],
        choices=lambda: get_form_ids(Subteam, add_null_id=True),
    )

    student_data: StudentDataForm = FormField(StudentDataForm)
    admin_data: AdminUserForm = FormField(AdminUserForm)

    submit = SubmitField("Register")
