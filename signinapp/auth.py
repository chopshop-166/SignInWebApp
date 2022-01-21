#!/usr/bin/env python

from flask import Blueprint, flash, redirect, url_for
from flask.templating import render_template
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired

from .model import Person, db, Role

login_manager = LoginManager()

auth = Blueprint("auth", __name__)


class RegisterForm(FlaskForm):
    name = StringField("name", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired()])
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    name = StringField("name", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired()])
    remember = BooleanField("remember")
    submit = SubmitField("Login")


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        print("Validated")
        # code to validate and add user to database goes here
        name = form.name.data
        password = form.password.data

        # if this returns a user, then the email already exists in database
        user = Person.get_canonical(name)

        # if a user is found, we want to redirect back to signup page so user can try again
        if user:
            flash("User already exists")
            return redirect(url_for('auth.register'))

        # Create a new user with the form data. Hash the password so the plaintext version isn't saved.
        new_user = Person.make(name=name, password=password,
                               role=Role.from_name("student"))

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template("register.html", form=form)


@auth.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        remember = form.remember.data

        # if this returns a user, then the email already exists in database
        user = Person.get_canonical(name)

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)

        return redirect('/')
    return render_template("login.html", form=form)


@auth.route('/logout')
def logout():
    logout_user()
    return redirect('/')


@auth.route('/usertest')
def usertest():
    if current_user.is_authenticated:
        return f"Signed in as {current_user.name}"
    return "Not signed in"
