from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    Field,
    Form,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
)
from wtforms.validators import DataRequired

from .model import ShirtSizes


class DataMaybeRequired(DataRequired):
    def __init__(self, message=None):
        super().__init__(message)

    def __call__(self, form, field: Field):
        if field.flags.is_required:
            return super().__call__(form, field)


class StudentDataForm(Form):
    graduation_year = IntegerField(
        "Graduation Year",
        validators=[DataRequired()],
        default=lambda: datetime.now().year + 3,
    )

    first_guardian_name = StringField("1st Parent Name", validators=[DataRequired()])
    first_guardian_phone_number = TelField(
        "1st Parent Phone Number", validators=[DataRequired()]
    )
    first_guardian_email = EmailField("1st Parent email", validators=[DataRequired()])

    second_guardian_name = StringField("2nd Parent Name")
    second_guardian_phone_number = TelField("2nd Parent Phone Number")
    second_guardian_email = EmailField("2nd Parent email")


class AdminUserForm(Form):
    role = SelectField()
    approved = BooleanField()
    active = BooleanField()


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])

    # Nasty hack to only require the validator to be used in one case
    password = PasswordField("Password", validators=[DataMaybeRequired()])

    name = StringField("Name", validators=[DataRequired()])
    preferred_name = StringField("Preferred Name")

    phone_number = TelField("Phone Number", validators=[DataRequired()])
    email = EmailField("Email Address", validators=[DataRequired()])
    address = StringField("Street Address", validators=[DataRequired()])
    tshirt_size = SelectField(
        "T-Shirt Size", choices=ShirtSizes.get_size_names(), validators=[DataRequired()]
    )
    subteam = SelectField("Subteam", validators=[DataRequired()])

    student_data = FormField(StudentDataForm)
    admin_data = FormField(AdminUserForm)

    submit = SubmitField("Register")
