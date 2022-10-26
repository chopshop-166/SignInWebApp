from __future__ import annotations

import dataclasses
import enum
from http import HTTPStatus
import locale
import re
import secrets
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from flask import Response, current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.future import select
from werkzeug.security import generate_password_hash
from wtforms import FieldList

from .util import (
    correct_time_for_storage,
    correct_time_from_storage,
    generate_grade_choices,
    normalize_phone_number_for_storage,
    normalize_phone_number_from_storage,
)


# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy()


def gen_code():
    "Generate an event code"
    return secrets.token_urlsafe(16)


def get_form_ids(model, add_null_id=False, filters=()):
    prefix = [(0, "None")] if add_null_id else []
    stmt = select(model)
    if filters:
        stmt = stmt.where(*filters)
    return prefix + [(x.id, x.name) for x in db.session.scalars(stmt)]


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
    emoji = db.Column(db.String)
    icon = db.Column(db.String)
    color = db.Column(db.String, default="black")

    awards: list[BadgeAward] = db.relationship("BadgeAward", back_populates="badge")

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

    owner: User = db.relationship("User", back_populates="awards", uselist=False)
    badge: Badge = db.relationship("Badge")

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

    code = db.Column(db.String, nullable=False, unique=True, default=gen_code)
    role_id = db.Column(db.Integer, db.ForeignKey("account_types.id"))
    approved = db.Column(db.Boolean, default=False)

    stamps: list[Stamps] = db.relationship("Stamps", back_populates="user")
    role: Role = db.relationship("Role", back_populates="users")
    subteam: Subteam = db.relationship("Subteam", back_populates="members")

    awards: list[BadgeAward] = db.relationship(
        "BadgeAward", back_populates="owner", cascade="all, delete-orphan"
    )
    badges: list[Badge] = association_proxy("awards", "badge")

    # Guardian specific data
    guardian_user_data: Guardian = db.relationship(
        "Guardian", back_populates="user", uselist=False
    )

    # Student specific data
    student_user_data: Student = db.relationship(
        "Student", back_populates="user", uselist=False
    )

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

    def award_badge(self, badge: Badge):
        "Assign a badge to a user"
        if badge not in self.badges:
            self.badges.append(badge)
            db.session.commit()

    def remove_badge(self, badge: Badge):
        "Remove a badge from a user"
        if badge in self.badges:
            self.badges.remove(badge)
            db.session.commit()

    def stamps_for(self, type_: EventType):
        "Get all stamps for an event type"
        return [s for s in self.stamps if (s.event.type_ == type_) & s.event.enabled]

    def total_stamps_for(self, type_: EventType) -> timedelta:
        "Total time for an event type"
        return sum((s.elapsed for s in self.stamps_for(type_)), start=timedelta())

    def stamps_for_event(self, event: Event) -> list[Stamps]:
        "Get all stamps for an event"
        return [s for s in self.stamps if s.event == event]

    def can_view(self, user: User):
        "Whether the user in question can view this user"
        return (
            self.role.mentor
            or self.role.admin
            or (self == user)
            or (
                self.guardian_user_data
                and user.student_user_data
                and user.student_user_data in self.guardian_user_data.students
            )
        )

    @property
    def human_readable(self) -> str:
        "Human readable string for display on a web page"
        return f"{'*' if self.role.mentor else ''}{self.display_name}"

    @property
    def display_name(self) -> str:
        return self.preferred_name or self.name

    @property
    def full_name(self) -> str:
        if self.preferred_name and self.preferred_name != self.name.split(" ")[0]:
            return f"{self.name} ({self.preferred_name})"
        return self.name

    def is_signed_into(self, code: str) -> bool:
        return bool(
            db.session.scalar(
                select(Active).where(Active.user == self, Active.event.has(code=code))
            )
        )

    @property
    def total_funds(self) -> str:
        all_funds = [ev.raw_funds_for(self) for ev in db.session.scalars(select(Event))]
        money = sum(all_funds, start=0.0)
        return locale.currency(money)

    @staticmethod
    def get_visible_users() -> list[User]:
        return db.session.scalars(select(User).where(User.role.has(visible=True)))

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
            role_id=role.id,
            subteam_id=subteam.id if subteam else 0,
            approved=approved,
            **kwargs,
        )
        db.session.add(user)
        db.session.flush()
        return user

    @staticmethod
    def make_guardian(name: str, phone_number: str, email: str):
        role = Role.from_name("guardian_limited")
        pn = normalize_phone_number_for_storage(phone_number)
        # Generate a username that *should* be unique.
        username = f"{name}_{pn}"
        guardian = User(
            name=name,
            username=username,
            role_id=role.id,
            phone_number=pn,
            email=email,
        )
        db.session.add(guardian)
        db.session.flush()
        return guardian

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
    user: User = db.relationship("User", back_populates="guardian_user_data")

    # Many to Many: Links Guardian to Children
    students: list[Student] = db.relationship(
        "Student", secondary=parent_child_association_table, back_populates="guardians"
    )

    @staticmethod
    def get_from(
        name: str, phone_number: str, email: str, contact_order: int
    ) -> Guardian:
        guardian_user = db.session.scalar(
            select(User).where(
                User.name == name,
                User.phone_number == phone_number,
                User.email == email,
            )
        )
        if guardian_user:
            # If we found the guardian user, then return the extra guardian data (This object/table)
            return guardian_user.guardian_user_data
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
    user: User = db.relationship("User", back_populates="student_user_data")

    # Many to Many: Links Student to Guardian
    guardians: list[Guardian] = db.relationship(
        "Guardian", secondary=parent_child_association_table, back_populates="students"
    )

    def add_guardian(self, guardian: Guardian):
        if guardian not in self.guardians:
            self.guardians.append(guardian)

    def update_guardians(self, gs: FieldList):
        self.guardians.clear()
        # Don't use enumerate in case they skip entries for some reason
        i = 0
        for guard in (guard.data for guard in gs):
            if guard["name"] and guard["phone_number"] and guard["email"]:
                i += 1
                self.add_guardian(
                    guardian=Guardian.get_from(
                        name=guard["name"],
                        phone_number=guard["phone_number"],
                        email=guard["email"],
                        contact_order=i,
                    )
                )

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
    code = db.Column(db.String, unique=True, default=gen_code)
    # Location the event takes place at
    location = db.Column(db.String)
    # Start time
    start = db.Column(db.DateTime, nullable=False)
    # End time
    end = db.Column(db.DateTime, nullable=False)
    # Event type
    type_id = db.Column(db.Integer, db.ForeignKey("event_types.id"))
    # Whether the event is enabled
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    # Whether users can register for the event
    registration_open = db.Column(db.Boolean, default=False)

    # Total funds for event, in cents
    funds = db.Column(db.Integer, default=0, nullable=False)
    # Total running cost for event, in cents
    cost = db.Column(db.Integer, default=0, nullable=False)
    # Percentage of funds that go to the team
    overhead = db.Column(db.Float, default=0.5, nullable=False)

    stamps: list[Stamps] = db.relationship("Stamps", back_populates="event")
    active: list[Active] = db.relationship("Active", back_populates="event")
    type_: EventType = db.relationship("EventType", back_populates="events")
    blocks: list[EventBlock] = db.relationship("EventBlock", back_populates="event")

    @staticmethod
    def get_from_code(event_code) -> Event | None:
        return db.session.scalar(select(Event).filter_by(code=event_code))

    @property
    def start_local(self) -> str:
        "Start time in local time zone"
        return correct_time_from_storage(self.start).strftime("%c")

    @property
    def end_local(self) -> str:
        "End time in local time zone"
        return correct_time_from_storage(self.end).strftime("%c")

    @property
    def funds_human(self) -> str:
        "Get the funds in a human readable format"
        return locale.currency(self.funds / 100.0)

    @property
    def cost_human(self) -> str:
        "Get the cost in a human readable format"
        return locale.currency(self.cost / 100.0)

    @hybrid_property
    def net_funds(self) -> int:
        "Get the net funds"
        return self.funds - self.cost

    @property
    def net_funds_human(self) -> str:
        "Get the net funds in a human readable format"
        return locale.currency(self.net_funds / 100.0)

    @property
    def adjusted_start(self) -> datetime:
        start = correct_time_from_storage(self.start)
        return start - timedelta(minutes=current_app.config["PRE_EVENT_ACTIVE_TIME"])

    @property
    def adjusted_end(self) -> datetime:
        end = correct_time_from_storage(self.end)
        return end + timedelta(minutes=current_app.config["POST_EVENT_ACTIVE_TIME"])

    @hybrid_property
    def is_active(self) -> bool:
        "Test for if the event is currently active"
        now = datetime.now(tz=timezone.utc)
        return self.enabled & (self.adjusted_start < now) & (now < self.adjusted_end)

    @is_active.expression
    def is_active(cls):
        "Usable in queries"
        return and_(
            cls.enabled,
            (
                func.datetime(
                    cls.start,
                    f"-{current_app.config['PRE_EVENT_ACTIVE_TIME']} minutes",
                )
                < func.now()
            ),
            (
                func.now()
                < func.datetime(
                    cls.end, f"+{current_app.config['POST_EVENT_ACTIVE_TIME']} minutes"
                )
            ),
        ).label("is_active")

    @property
    def total_time(self) -> timedelta:
        return sum((s.elapsed for s in self.stamps), start=timedelta())

    def raw_funds_for(self, user: User) -> float:
        "Calculate funds from an event for the given user"
        if not user.role.receives_funds:
            return 0.0
        user_stamps = user.stamps_for_event(self)
        user_hours = sum((stamp.elapsed for stamp in user_stamps), start=timedelta())
        total_hours = sum(
            (stamp.elapsed for stamp in self.stamps if stamp.user.role.receives_funds),
            start=timedelta(),
        )
        user_proportion = (user_hours / total_hours) if total_hours else 0.0
        return user_proportion * (1 - self.overhead) * self.net_funds / 100.0

    def funds_for(self, user: User) -> str:
        return locale.currency(self.raw_funds_for(user))

    @property
    def overhead_funds(self) -> str:
        return locale.currency(self.net_funds * self.overhead / 100.0)

    def scan(self, user_code) -> StampEvent:
        if not self.is_active:
            return Response("Error: Event is not active", HTTPStatus.BAD_REQUEST)

        if not user_code:
            return Response(
                f"Error: Not a valid QR code: {user_code}", HTTPStatus.BAD_REQUEST
            )

        user = db.session.scalar(select(User).filter_by(code=user_code))
        if not user:
            return Response("Error: User does not exist", HTTPStatus.BAD_REQUEST)
        if not user.approved:
            return Response("Error: User is not approved", HTTPStatus.BAD_REQUEST)

        active = db.session.scalar(
            select(Active).where(Active.user == user, Active.event == self)
        )

        if active:
            stamp = create_stamp_from_active(active, None)
            # Elapsed needs to be taken after committing to the DB
            # otherwise it won't be populated
            sign = f"out after {stamp.elapsed}"
            return StampEvent(user.human_readable, sign)

        active = Active(user=user, event=self)
        db.session.add(active)
        db.session.commit()
        return StampEvent(user.human_readable, "in")

    @staticmethod
    def create(
        name: str,
        description: str,
        location: str,
        start: datetime,
        end: datetime,
        event_type: EventType | str,
        code: int = None,
        registration_open: bool = False,
    ):
        start = correct_time_for_storage(start)
        end = correct_time_for_storage(end)

        if isinstance(event_type, str):
            event_type = EventType.from_name(event_type)

        ev = Event(
            name=name,
            description=description,
            location=location,
            start=start,
            end=end,
            type_=event_type,
            code=code,
            registration_open=registration_open,
        )
        db.session.add(ev)
        db.session.flush()

        # Add default block for the entire event time
        block = EventBlock(start=start, end=end, event_id=ev.id)
        db.session.add(block)
        return ev


def create_stamp_from_active(active: Active, end: datetime):
    stamp = Stamps(
        user=active.user,
        event=active.event,
        start=active.start,
        end=end,
    )
    db.session.delete(active)
    db.session.add(stamp)
    db.session.commit()
    return stamp


class EventType(db.Model):
    __tablename__ = "event_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    autoload = db.Column(db.Boolean, nullable=False, default=False)

    events: list[Event] = db.relationship("Event", back_populates="type_")

    @staticmethod
    def from_name(name: str) -> EventType:
        return db.session.scalar(select(EventType).filter_by(name=name))


class Active(db.Model):
    __tablename__ = "active"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    user: User = db.relationship("User")
    event: Event = db.relationship("Event")

    @property
    def start_local(self) -> str:
        "Start time in local time zone"
        return correct_time_from_storage(self.start).strftime("%c")

    def as_dict(self):
        "Return a dictionary for sending to the web page"
        return {
            "user": self.user.human_readable,
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

    user: User = db.relationship("User", back_populates="stamps")
    event: Event = db.relationship("Event", back_populates="stamps")

    @hybrid_property
    def elapsed(self) -> timedelta:
        "Elapsed time for a stamp"
        return self.end - self.start

    def as_dict(self):
        "Return a dictionary for sending to the web page"
        return {
            "user": self.user.human_readable,
            "elapsed": str(self.elapsed),
            "start": correct_time_from_storage(self.start),
            "end": correct_time_from_storage(self.end),
            "event": self.event.name,
        }

    def as_list(self):
        "Return a list for sending to the web page"
        return [
            self.user.human_readable,
            correct_time_from_storage(self.start),
            correct_time_from_storage(self.end),
            self.elapsed,
            self.event.name,
            self.event.type_.name,
        ]

    @staticmethod
    def get(user: User | None = None, event_code=None):
        "Get stamps matching a requirement"
        stmt = select(Stamps).where(Stamps.event.has(enabled=True))
        if event_code:
            stmt = stmt.where(Stamps.event.has(code=event_code))
        if user:
            stmt = stmt.where(Stamps.user == user)
        return [s.as_dict() for s in db.session.scalars(stmt)]

    @staticmethod
    def export(
        user: User | None = None,
        start: datetime = None,
        end: datetime = None,
        type_: str = None,
        subteam: Subteam = None,
        headers=True,
    ) -> list[list[str]]:
        stmt = select(Stamps).filter(Stamps.event.has(enabled=True))
        if user:
            stmt = stmt.where(Stamps.user.code == user.code)
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
    receives_funds = db.Column(db.Boolean, nullable=False, default=False)

    users: list[User] = db.relationship("User", back_populates="role")

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

    members: list[User] = db.relationship("User", back_populates="subteam")

    @staticmethod
    def from_name(name) -> Subteam:
        "Get a subteam by name"
        return db.session.scalar(select(Subteam).filter_by(name=name))


class EventRegistration(db.Model):
    __tablename__ = "eventregistrations"
    id = db.Column(db.Integer, primary_key=True)

    # Link to event block
    event_block_id = db.Column(db.Integer, db.ForeignKey("eventblocks.id"))
    event_block: EventBlock = db.relationship(
        "EventBlock", back_populates="registrations"
    )
    # Link to user
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user: User = db.relationship("User")
    # User comment for event block
    comment = db.Column(db.String)

    registered = db.Column(db.Boolean)

    @staticmethod
    def upsert(
        event_block_id: int,
        user: User,
        comment: str,
        registered: bool,
    ):
        existing_registration = db.session.scalar(
            select(EventRegistration).filter_by(
                user=user, event_block_id=event_block_id
            )
        )
        if existing_registration:
            existing_registration.registered = registered
            existing_registration.comment = comment
        else:
            registration = EventRegistration(
                event_block_id=event_block_id,
                user=user,
                comment=comment,
                registered=registered,
            )
            db.session.add(registration)


class EventBlock(db.Model):
    __tablename__ = "eventblocks"
    id = db.Column(db.Integer, primary_key=True)

    # Start Time for block
    start = db.Column(db.DateTime)
    # End time for block
    end = db.Column(db.DateTime)
    # Link to Event
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    event: Event = db.relationship("Event", back_populates="blocks")

    registrations: EventRegistration = db.relationship(
        "EventRegistration", back_populates="event_block"
    )
