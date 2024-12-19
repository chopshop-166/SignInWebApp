from collections import defaultdict
from datetime import datetime

import flask_excel as excel
from flask import Blueprint, Flask, request
from flask.templating import render_template
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.future import select

from .model import Role, ShirtSizes, Student, Subteam, User, db
from .util import admin_required, get_current_graduation_years, mentor_required

team = Blueprint("team", __name__)


@team.route("/users")
@mentor_required
def users():
    users = User.get_visible_users()
    roles = db.session.scalars(select(Role))
    return render_template("users.html.jinja2", users=users, roles=roles)


@team.route("/shirts")
@mentor_required
def shirts():
    shirts = defaultdict(lambda: defaultdict(lambda: 0))
    for size in ShirtSizes:
        shirts[size]
    for u in User.get_visible_users():
        if u.tshirt_size:
            shirts[u.tshirt_size][u.role] += 1
    return render_template("shirts.html.jinja2", shirts=shirts)


@team.route("/subteam")
@login_required
def subteam():
    st_id = request.args.get("st_id")
    subteam = db.session.get(Subteam, st_id)
    return render_template("subteam.html.jinja2", subteam=subteam)


@team.route("/users/students")
@mentor_required
def list_students():
    include_all = request.args.get("include_all", False) == "true"
    select_stmt = select(User).where(or_(User.role.has(name="student"), User.role.has(name="lead")))
    if not include_all:
        select_stmt = select_stmt.join(Student).where(
            Student.graduation_year.in_(get_current_graduation_years())
        )
    users = db.session.scalars(select_stmt.order_by(User.name)).all()
    return render_template("user_list.html.jinja2", role="Student", users=users)


@team.route("/users/guardians")
@mentor_required
def list_guardians():
    include_all = request.args.get("include_all", False) == "true"
    users = db.session.scalars(
        select(User).where(User.role.has(guardian=True)).order_by(User.name)
    ).all()
    if not include_all:
        users = [
            guardian
            for guardian in users
            if any(
                student
                for student in guardian.guardian_user_data.students
                if student.graduation_year in get_current_graduation_years()
            )
        ]
    return render_template("user_list.html.jinja2", role="Guardian", users=users)


@team.route("/users/mentors")
@mentor_required
def list_mentors():
    users = db.session.scalars(
        select(User).where(User.role.has(mentor=True)).order_by(User.name)
    ).all()
    return render_template("user_list.html.jinja2", role="Mentor", users=users)


@team.route("/users/students/export")
@admin_required
def students_export():
    result = [
        [
            "Student Name",
            "Email",
            "First Parent Name",
            "First Parent Email",
            "Second Parent Name",
            "Second Parent Email",
        ]
    ] + [
        [
            student.user.full_name,
            student.user.email,
            student.guardians[0].user.name if student.guardians else "",
            student.guardians[0].user.email if student.guardians else "",
            student.guardians[1].user.name if len(student.guardians) > 1 else "",
            student.guardians[1].user.email if len(student.guardians) > 1 else "",
        ]
        for student in db.session.scalars(
            select(Student)
            .where(Student.graduation_year.in_(get_current_graduation_years()))
            .order_by(Student.user_id)
        )
    ]
    return excel.make_response_from_array(
        result,
        "csv",
        file_name=f"students-parents-{datetime.now().strftime('%Y-%m-%d')}.csv",
    )


def init_app(app: Flask):
    app.register_blueprint(team)
