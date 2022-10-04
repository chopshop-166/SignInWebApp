from flask_wtf import FlaskForm
from flask import escape
from wtforms import (
    BooleanField,
    EmailField,
    Field,
    Form,
    FormField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
)
from wtforms.validators import DataRequired

from .model import ShirtSizes, generate_grade_choices


def sanitize(string):
    return "" if (string is None) else escape(string)


class DataMaybeRequired(DataRequired):
    def __init__(self, message=None):
        super().__init__(message)

    def __call__(self, form, field: Field):
        if field.flags.is_required:
            return super().__call__(form, field)


class StudentDataForm(Form):
    graduation_year = SelectField(
        "Graduation Year",
        validators=[DataRequired()],
        filters=[sanitize],
        choices=lambda: generate_grade_choices().items(),
    )

    first_guardian_name = StringField(
        "1st Parent Name", validators=[DataRequired()], filters=[sanitize]
    )
    first_guardian_phone_number = TelField(
        "1st Parent Phone Number", validators=[DataRequired()], filters=[sanitize]
    )
    first_guardian_email = EmailField(
        "1st Parent email", validators=[DataRequired()], filters=[sanitize]
    )

    second_guardian_name = StringField("2nd Parent Name", filters=[sanitize])
    second_guardian_phone_number = TelField(
        "2nd Parent Phone Number", filters=[sanitize]
    )
    second_guardian_email = EmailField("2nd Parent email", filters=[sanitize])


class AdminUserForm(Form):
    role = SelectField()
    approved = BooleanField()
    active = BooleanField()


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()], filters=[sanitize])

    # Nasty hack to only require the validator to be used in one case
    password = PasswordField("Password", validators=[DataMaybeRequired()])

    name = StringField("Name", validators=[DataRequired()], filters=[sanitize])
    preferred_name = StringField(
        "Preferred Name", description="Leave blank for none", filters=[sanitize]
    )

    phone_number = TelField(
        "Phone Number", validators=[DataRequired()], filters=[sanitize]
    )
    email = EmailField("Email Address", validators=[DataRequired()], filters=[sanitize])
    address = StringField(
        "Street Address", validators=[DataRequired()], filters=[sanitize]
    )
    tshirt_size = SelectField(
        "T-Shirt Size",
        choices=ShirtSizes.get_size_names(),
        validators=[DataRequired()],
        filters=[sanitize],
    )
    subteam = SelectField("Subteam", validators=[DataRequired()], filters=[sanitize])

    student_data = FormField(StudentDataForm)
    admin_data = FormField(AdminUserForm)

    submit = SubmitField("Register")
