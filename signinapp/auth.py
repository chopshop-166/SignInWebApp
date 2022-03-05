from flask import Blueprint, flash, redirect, url_for
from flask.templating import render_template
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo

from .model import Role, User, db

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table,
    # use it in the query for the user
    user = User.query.get(int(user_id))
    if user.approved:
        return user


auth = Blueprint("auth", __name__)


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    new_password_rep = PasswordField("New Password (again)",
                                     validators=[DataRequired(),
                                                 EqualTo("new_password", message='Passwords must match')])
    submit = SubmitField()


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # code to validate and add user to database goes here
        name = form.name.data
        password = form.password.data

        # if this returns a user, then the user already exists in database
        user = User.get_canonical(name)

        # if a user is found, we want to redirect back to signup page
        # so the user can try again
        if user:
            flash("User already exists")
            return redirect(url_for('auth.register'))

        # Create a new user with the form data.
        # Hash the password so the plaintext version isn't saved.
        new_user = User.make(name=name, password=password,
                             role=Role.get_default())

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template("auth/register.html.jinja2", form=form)


@auth.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        remember = form.remember.data

        # if this returns a user, then the email already exists in database
        user = User.get_canonical(name)

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        if not user.approved:
            flash('User is not approved')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)

        return redirect('/')
    return render_template("auth/login.html.jinja2", form=form)


@auth.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@auth.route("/password", methods=["GET", "POST"])
@login_required
def password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password, form.current_password.data):
            flash("Incorrect current password")
            return redirect(url_for("auth.password"))

        current_user.password = generate_password_hash(form.new_password.data)
        db.session.commit()
        return redirect(url_for('user.profile'))

    return render_template("auth/password.html.jinja2", form=form)
