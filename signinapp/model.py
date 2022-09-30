from __future__ import annotations

import base64
import dataclasses
import datetime
import enum
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.future import select
from werkzeug.security import generate_password_hash

from .util import (
    correct_time_for_storage,
    correct_time_from_storage,
    generate_grade_choices,
    normalize_phone_number_for_storage,
    normalize_phone_number_from_storage,
)

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy()

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$"
)

HASH_RE = re.compile(r"^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$")


def mk_hash(name: str):
    "Make a user hash"
    return base64.b64encode(name.lower().encode("utf-8")).decode("utf-8")


def event_code():
    "Generate an event code"
    return secrets.token_urlsafe(16)


def canonical_name(name: str):
    "Attempt to get a user string"
    if m := HASH_RE.match(name):
        return name
    if m := NAME_RE.match(name):
        return mk_hash(f"{m['first']} {m['last']}")


def get_form_ids(model, add_null_id=False):
    return ([(0, "None")] if add_null_id else []) + [
        (x.id, x.name) for x in db.session.scalars(select(model))
    ]


@dataclasses.dataclass
class StampEvent:
    name: str
    event: str


class ShirtSizes(enum.Enum):
    Small = "Small"
    Medium = "Medium"
    Large = "Large"
    X_Large = "X-Large"
    XX_Large = "XX-Large"
    XXX_Large = "XXX-Large"

    @classmethod
    def get_size_names(cls):
        return [(size.name, size.value) for size in cls]


class Badge(db.Model):
    'Represents an "achievement", accomplishment, or certification'
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    icon = db.Column(db.String)
    color = db.Column(db.String, default="black")

    awards = db.relationship("BadgeAward", back_populates="badge")

    @staticmethod
    def from_name(name) -> Badge:
        "Get a badge by name"
        return db.session.scalar(select(Badge).filter_by(name=name))


class BadgeAward(db.Model):
    "Represents a pairing of user to badge, with received date"
    __tablename__ = "badge_awards"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"), primary_key=True)
    received = db.Column(db.DateTime, server_default=func.now())

    owner = db.relationship("User", back_populates="awards", uselist=False)
    badge = db.relationship("Badge")

    def __init__(self, badge=None, owner=None):
        self.owner = owner
        self.badge = badge


parent_child_association_table = db.Table(
    "parent_child_association",
    db.metadata,
    db.Column("guardians", db.ForeignKey("guardians.id"), primary_key=True),
    db.Column("user_id", db.ForeignKey("students.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    preferred_name = db.Column(db.String)
    password = db.Column(db.String)
    subteam_id = db.Column(db.Integer, db.ForeignKey("subteams.id"))
    phone_number = db.Column(db.String)
    email = db.Column(db.String)
    address = db.Column(db.String)
    tshirt_size = db.Column(db.Enum(ShirtSizes))

    code = db.Column(db.String, nullable=False, unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("account_types.id"))
    approved = db.Column(db.Boolean, default=False)

    stamps = db.relationship("Stamps", back_populates="user")
    role = db.relationship("Role")
    subteam = db.relationship("Subteam", back_populates="members")

    awards = db.relationship(
        "BadgeAward", back_populates="owner", cascade="all, delete-orphan"
    )
    badges = association_proxy("awards", "badge")

    # Guardian specific data
    guardian_user_data = db.relationship(
        "Guardian", back_populates="user", uselist=False
    )

    # Student specific data
    student_user_data = db.relationship("Student", back_populates="user", uselist=False)

    @hybrid_property
    def is_active(self) -> bool:
        "Required by Flask-Login"
        return self.approved

    @property
    def total_time(self) -> timedelta:
        "Total time for all stamps"
        return sum((s.elapsed for s in self.stamps), start=timedelta())

    @property
    def formatted_phone_number(self) -> str:
        return normalize_phone_number_from_storage(self.phone_number)

    def has_badge(self, badge_id: int) -> bool:
        "Test if a badge is assigned to a user"
        badge = db.session.get(Badge, badge_id)
        return badge in self.badges

    def award_badge(self, badge_id: int):
        "Assign a badge to a user"
        if not self.has_badge(badge_id):
            badge = db.session.get(Badge, badge_id)
            self.badges.append(badge)
            db.session.commit()

    def remove_badge(self, badge_id: int):
        "Remove a badge from a user"
        if self.has_badge(badge_id):
            badge = db.session.get(Badge, badge_id)
            self.badges.remove(badge)
            db.session.commit()

    def stamps_for(self, type_: EventType):
        "Get all stamps for an event type"
        return [s for s in self.stamps if (s.event.type_ == type_) & s.event.enabled]

    def total_stamps_for(self, type_: EventType) -> timedelta:
        "Total time for an event type"
        return sum((s.elapsed for s in self.stamps_for(type_)), start=timedelta())

    @hybrid_method
    def can_view(self, user: User):
        "Whether the user in question can view this user"
        return self.role.mentor | self.role.admin | (self == user)

    @property
    def human_readable(self) -> str:
        "Human readable string for display on a web page"
        return f"{'*' if self.role.mentor else ''}{self.display_name}"

    @property
    def display_name(self) -> str:
        return self.preferred_name or self.name

    @staticmethod
    def get_visible_users() -> list[User]:
        return db.session.scalars(select(User).join(Role).where(Role.visible == True))

    @staticmethod
    def make(
        username: str,
        name: str,
        password: str,
        role: Role,
        approved=False,
        subteam=None,
        **kwargs,
    ) -> User:
        "Make a user, with password and hash"
        if "phone_number" in kwargs:
            kwargs["phone_number"] = normalize_phone_number_for_storage(
                kwargs["phone_number"]
            )
        user = User(
            username=username,
            name=name,
            password=generate_password_hash(password),
            code=mk_hash(name),
            role_id=role.id,
            subteam_id=subteam.id if subteam else 0,
            approved=approved,
            **kwargs,
        )
        db.session.add(user)
        db.session.flush()
        return user

    @staticmethod
    def make_guardian(name: str, phone_number: str, email: str, contact_order: int = 1):
        role = Role.from_name("guardian_limited")
        # Generate a username that *should* be unique.
        username = f"{name}_{normalize_phone_number_for_storage(phone_number)}"
        guardian = User(
            name=name,
            username=username,
            code=mk_hash(name),
            role_id=role.id,
            phone_number=normalize_phone_number_for_storage(phone_number),
            email=email,
        )
        db.session.add(guardian)
        db.session.flush()
        return guardian

    @staticmethod
    def get_canonical(name) -> User | None:
        "Look up user by name"
        code = mk_hash(name)
        return db.session.scalar(select(User).filter_by(code=code))

    @staticmethod
    def from_username(username) -> User | None:
        "Look up user by username"
        return db.session.scalar(select(User).filter_by(username=username))


class Guardian(db.Model):
    """
    This table is a bit strange as it has a one to one link with a User (Parent) as well as
    Many to Many links with User (Children).

    """

    __tablename__ = "guardians"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    contact_order = db.Column(db.Integer)

    # One to One: Links User to row in Guardian table
    user = db.relationship("User", back_populates="guardian_user_data")

    # Many to Many: Links Guardian to Children
    students = db.relationship(
        "Student", secondary=parent_child_association_table, back_populates="guardians"
    )

    @staticmethod
    def get_from(
        name: str, phone_number: str, email: str, contact_order: int
    ) -> Guardian:
        guardian = User.get_canonical(name)
        if guardian:
            # If we found the guardian user, then return the extra guardian data (This object/table)
            return guardian.guardian_user_data
        # Create the guardian user, and add the guardian user object
        guardian = User.make_guardian(name=name, phone_number=phone_number, email=email)
        guardian_user_data = Guardian(user_id=guardian.id, contact_order=contact_order)
        guardian.guardian_user_data = guardian_user_data
        db.session.add(guardian_user_data)
        return guardian_user_data


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Extra student information
    graduation_year = db.Column(db.Integer)

    # One to One: Links User to extra student information
    user = db.relationship("User", back_populates="student_user_data")

    # Many to Many: Links Student to Guardian
    guardians = db.relationship(
        "Guardian", secondary=parent_child_association_table, back_populates="students"
    )

    def add_guardian(self, guardian: Guardian):
        if guardian not in self.guardians:
            self.guardians.append(guardian)

    @property
    def display_grade(self):
        grades = generate_grade_choices()
        if self.graduation_year in grades:
            return grades[self.graduation_year]
        else:
            return f"Alumni (Graduated: {self.graduation_year})"

    @staticmethod
    def make(
        username: str, name: str, password: str, graduation_year: int, **kwargs
    ) -> User:
        role = Role.from_name("student")
        student = User.make(
            name=name, username=username, password=password, role=role, **kwargs
        )
        student_user_data = Student(user_id=student.id, graduation_year=graduation_year)

        student.student_user_data = student_user_data
        db.session.add(student_user_data)
        return student


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    # User-visible name
    name = db.Column(db.String)
    # Description of the event
    description = db.Column(db.String, default="")
    # Unique code for tracking
    code = db.Column(db.String, unique=True)
    # Location the event takes place at
    location = db.Column(db.String)
    # Start time
    start = db.Column(db.DateTime)
    # End time
    end = db.Column(db.DateTime)
    # Event type
    type_id = db.Column(db.Integer, db.ForeignKey("event_types.id"))
    # Whether the event is enabled
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    stamps = db.relationship("Stamps", back_populates="event")
    active = db.relationship("Active", back_populates="event")
    type_ = db.relationship("EventType", back_populates="events")

    @property
    def start_local(self) -> str:
        "Start time in local time zone"
        return correct_time_from_storage(self.start).strftime("%c")

    @property
    def end_local(self) -> str:
        "End time in local time zone"
        return correct_time_from_storage(self.end).strftime("%c")

    @hybrid_property
    def is_active(self) -> bool:
        "Test for if the event is currently active"
        now = datetime.now(tz=timezone.utc)
        start = correct_time_from_storage(self.start)
        end = correct_time_from_storage(self.end)
        return self.enabled & (start < now) & (now < end)

    @is_active.expression
    def is_active(cls):
        "Usable in queries"
        return and_(
            cls.enabled, (cls.start < func.now()), (func.now() < cls.end)
        ).label("is_active")

    def scan(self, name) -> StampEvent:
        if not self.is_active:
            return

        code = canonical_name(name)
        if not code:
            return

        user = db.session.scalar(select(User).filter_by(code=code))
        if not (user and user.approved):
            return

        active = db.session.scalar(
            select(Active).where(Active.user == user, Active.event == self)
        )
        if not active:
            active = Active(user=user, event=self)
            db.session.add(active)
            db.session.commit()
            return StampEvent(user.human_readable(), "in")

        stamp = Stamps(user=user, event=self, start=active.start)
        db.session.delete(active)
        db.session.add(stamp)
        db.session.commit()
        # Elapsed needs to be taken after committing to the DB
        # otherwise it won't be populated
        sign = f"out after {stamp.elapsed}"
        return StampEvent(user.human_readable(), sign)


class EventType(db.Model):
    __tablename__ = "event_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    autoload = db.Column(db.Boolean, nullable=False, default=False)

    events = db.relationship("Event", back_populates="type_")


class Active(db.Model):
    __tablename__ = "active"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    user = db.relationship("User")
    event = db.relationship("Event")

    @property
    def start_local(self) -> str:
        "Start time in local time zone"
        return correct_time_from_storage(self.start).strftime("%c")

    def as_dict(self):
        "Return a dictionary for sending to the web page"
        return {
            "user": self.user.human_readable(),
            "start": self.start,
            "event": self.event.name,
        }

    @staticmethod
    def get(event_code=None) -> list[dict]:
        stmt = select(Active)
        if event_code:
            stmt = stmt.filter(Active.event.has(code=event_code))
        return [active.as_dict() for active in db.session.scalars(stmt)]


class Stamps(db.Model):
    __tablename__ = "stamps"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("users.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime, server_default=func.now())

    user = db.relationship("User", back_populates="stamps")
    event = db.relationship("Event", back_populates="stamps")

    @hybrid_property
    def elapsed(self) -> timedelta:
        "Elapsed time for a stamp"
        return self.end - self.start

    def as_dict(self):
        "Return a dictionary for sending to the web page"
        return {
            "user": self.user.human_readable(),
            "elapsed": str(self.elapsed),
            "start": correct_time_from_storage(self.start),
            "end": correct_time_from_storage(self.end),
            "event": self.event.name,
        }

    def as_list(self):
        "Return a list for sending to the web page"
        return [
            self.user.human_readable(),
            correct_time_from_storage(self.start),
            correct_time_from_storage(self.end),
            self.elapsed,
            self.event.name,
            self.event.type_.name,
        ]

    @staticmethod
    def get(name=None, event_code=None):
        "Get stamps matching a requirement"
        stmt = select(Stamps).where(Stamps.event.enabled == True)
        if event_code:
            stmt = stmt.where(Stamps.event.code == event_code)
        if name:
            user_code = canonical_name(name)
            stmt = stmt.where(Stamps.user.code == user_code)
        return [s.as_dict() for s in db.session.scalars(stmt)]

    @staticmethod
    def export(
        name: str = None,
        start: datetime = None,
        end: datetime = None,
        type_: str = None,
        subteam: Subteam = None,
        headers=True,
    ) -> list[list[str]]:
        stmt = select(Stamps).filter(Stamps.event.has(enabled=True))
        if name:
            code = mk_hash(name)
            stmt = stmt.where(Stamps.user.code == code)
        if start:
            stmt = stmt.where(Stamps.start < correct_time_for_storage(start))
        if end:
            stmt = stmt.where(Stamps.end > correct_time_for_storage(end))
        if type_:
            stmt = stmt.where(Stamps.event.has(type_=type_))
        if subteam:
            stmt.where(Stamps.user.subteam == subteam)
        result = [stamp.as_list() for stamp in db.session.scalars(stmt)]
        if headers:
            result = [
                ["Name", "Start", "End", "Elapsed", "Event", "Event Type"]
            ] + result
        return result


class Role(db.Model):
    __tablename__ = "account_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    admin = db.Column(db.Boolean, nullable=False, default=False)
    mentor = db.Column(db.Boolean, nullable=False, default=False)
    guardian = db.Column(db.Boolean, nullable=False, default=False)
    can_display = db.Column(db.Boolean, nullable=False, default=False)
    autoload = db.Column(db.Boolean, nullable=False, default=False)
    can_see_subteam = db.Column(db.Boolean, nullable=False, default=False)
    default_role = db.Column(db.Boolean, nullable=False, default=False)
    visible = db.Column(db.Boolean, nullable=False, default=True)

    @staticmethod
    def from_name(name) -> Role:
        "Get a role by name"
        return db.session.scalar(select(Role).filter_by(name=name))

    @staticmethod
    def get_default() -> Role:
        "Get the default role"
        return db.session.scalar(select(Role).filter_by(default_role=True))

    @staticmethod
    def set_default(def_role):
        "Set the default role"
        for role in db.session.scalar(select(Role)):
            role.default_role = role == def_role
        db.session.commit()

    @staticmethod
    def get_visible() -> list[Role]:
        return db.session.scalars(select(Role).filter_by(visible=True))


class Subteam(db.Model):
    __tablename__ = "subteams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    members = db.relationship("User", back_populates="subteam")

    @staticmethod
    def from_name(name) -> Subteam:
        "Get a subteam by name"
        return db.session.scalar(select(Subteam).filter_by(name=name))
