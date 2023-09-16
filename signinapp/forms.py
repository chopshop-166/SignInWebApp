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

from signinapp.util import normalize_phone_number_for_storage

from .model import (
    Pronoun,
    Role,
    ShirtSizes,
    Subteam,
    User,
    generate_grade_choices,
    get_form_ids,
)

NAME_RE = regex.compile(r"^(\p{L}+(['\-]\p{L}+)*)( \p{L}+(['\-]\p{L}+)*)*$")
ADDRESS_RE = regex.compile(r"[A-Za-z0-9'\.\-\s\,]+")
PHONE_RE = regex.compile(r"^(\d{10})?$")


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
        description="First and Last Names",
        validators=[Optional(), Regexp(NAME_RE)],
        filters=[strip],
    )
    phone_number = TelField(
        "Phone Number",
        filters=[normalize_phone_number_for_storage],
        validators=[Regexp(PHONE_RE)],
        render_kw={"placeholder": "555-555-5555"},
    )
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
    email = EmailField(
        "Email Address",
        validators=[DataRequired(), Email()],
        description="Preferably a non-school address",
    )
    password = PasswordField("Password")

    name = StringField(
        "Name",
        description="First and Last Names",
        validators=[
            DataRequired(),
            Regexp(NAME_RE),
        ],
        filters=[strip],
    )
    preferred_name = StringField(
        "Preferred Name",
        description="Leave blank for none",
        validators=[
            Optional(),
            Regexp(NAME_RE),
        ],
        filters=[strip],
    )

    phone_number = TelField(
        "Phone Number",
        filters=[normalize_phone_number_for_storage],
        validators=[Regexp(PHONE_RE)],
        render_kw={"placeholder": "555-555-5555"},
    )
    address = StringField(
        "Street Address", validators=[DataRequired(), Regexp(ADDRESS_RE)]
    )
    tshirt_size = SelectField(
        "T-Shirt Size", choices=ShirtSizes.get_size_names(), validators=[DataRequired()]
    )
    pronouns = SelectField(
        "Pronouns", choices=Pronoun.get_pronoun_options(), validators=[DataRequired()]
    )
    subteam = SelectField(
        "Subteam",
        validators=[DataRequired()],
        choices=lambda: get_form_ids(Subteam, add_null_id=True),
    )

    student_data: StudentDataForm = FormField(StudentDataForm)
    admin_data: AdminUserForm = FormField(AdminUserForm)

    submit = SubmitField("Register")
