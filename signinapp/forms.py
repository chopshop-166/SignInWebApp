from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    Form,
    FormField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
)
from wtforms.validators import DataRequired, Email, Regexp, Length

from .model import Role, ShirtSizes, Subteam, User, generate_grade_choices, get_form_ids


class StudentDataForm(Form):
    graduation_year = SelectField(
        "Graduation Year",
        validators=[DataRequired()],
        choices=lambda: generate_grade_choices().items(),
    )

    first_guardian_name = StringField(
        "1st Parent Name", validators=[DataRequired()], filters=[str.strip]
    )
    first_guardian_phone_number = TelField(
        "1st Parent Phone Number", validators=[DataRequired()]
    )
    first_guardian_email = EmailField(
        "1st Parent email", validators=[DataRequired(), Email()]
    )

    second_guardian_name = StringField("2nd Parent Name", filters=[str.strip])
    second_guardian_phone_number = TelField("2nd Parent Phone Number")
    second_guardian_email = EmailField("2nd Parent email", validators=[Email()])


class AdminUserForm(Form):
    role = SelectField(choices=lambda: get_form_ids(Role))
    approved = BooleanField()


class UserForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Regexp(r"\w+")], filters=[str.strip]
    )
    password = PasswordField("Password", validators=[Length(8)])

    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Regexp(r"([A-Za-z]+(['\-][A-Za-z])*)( [A-Za-z]+(['\-][A-Za-z])*)*"),
        ],
        filters=[str.strip],
    )
    preferred_name = StringField(
        "Preferred Name", description="Leave blank for none", filters=[str.strip]
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
