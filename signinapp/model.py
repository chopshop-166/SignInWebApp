from __future__ import annotations

import dataclasses
import enum
import locale
import secrets
from datetime import date, datetime, timedelta, timezone
from http import HTTPStatus
from typing import Annotated

from flask import Response, current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func, MetaData
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash
from wtforms import FieldList

from .util import (
    correct_time_for_storage,
    correct_time_from_storage,
    generate_grade_choices,
    normalize_phone_number_for_storage,
    normalize_phone_number_from_storage,
)


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy(metadata=metadata)

intpk = Annotated[int, mapped_column(primary_key=True)]
NonNullBool = Annotated[bool, mapped_column(default=False)]


def school_year_for_date(d: date):
    year = d.year
    if d.month > 6:
        year += 1
    return year


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


class Pronoun(enum.Enum):
    He_Him = "He/Him"
    She_Her = "She/Her"
    They_Them = "They/Them"
    He_They = "He/They"
    She_They = "She/They"

    @classmethod
    def get_pronoun_options(cls):
        return [(p.name, p.value) for p in cls]


class Badge(db.Model):
    'Represents an "achievement", accomplishment, or certification'
    __tablename__ = "badges"
    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str | None]
    emoji: Mapped[str | None]
    icon: Mapped[str | None]
    color: Mapped[str] = mapped_column(default="black")

    awards: Mapped[list[BadgeAward]] = db.relationship(back_populates="badge")

    @staticmethod
    def from_name(name) -> Badge:
        "Get a badge by name"
        return db.session.scalar(select(Badge).filter_by(name=name))


class BadgeAward(db.Model):
    "Represents a pairing of user to badge, with received date"
    __tablename__ = "badge_awards"
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), primary_key=True)
    badge_id: Mapped[int] = mapped_column(db.ForeignKey("badges.id"), primary_key=True)
    received: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped[User] = db.relationship(back_populates="awards", uselist=False)
    badge: Mapped[Badge] = db.relationship()

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
    id: Mapped[intpk]
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    preferred_name: Mapped[str | None]
    password: Mapped[str | None]
    subteam_id: Mapped[int | None] = mapped_column(db.ForeignKey("subteams.id"))
    phone_number: Mapped[str | None]
    address: Mapped[str | None]
    tshirt_size: Mapped[ShirtSizes | None]
    pronouns: Mapped[Pronoun | None]

    code: Mapped[str] = mapped_column(unique=True, default=gen_code)
    role_id: Mapped[int] = mapped_column(db.ForeignKey("account_types.id"))
    approved: Mapped[NonNullBool]

    stamps: Mapped[list[Stamps]] = db.relationship(
        "Stamps",
        back_populates="user",
        cascade="all, delete, delete-orphan",
    )
    role: Mapped[Role] = db.relationship(back_populates="users")
    subteam: Mapped[Subteam] = db.relationship(back_populates="members")

    awards: Mapped[list[BadgeAward]] = db.relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    badges: AssociationProxy[list[Badge]] = association_proxy("awards", "badge")

    # Guardian specific data
    guardian_user_data: Mapped[Guardian | None] = db.relationship(
        back_populates="user",
        cascade="all, delete, delete-orphan",
    )

    # Student specific data
    student_user_data: Mapped[Student | None] = db.relationship(
        back_populates="user",
        cascade="all, delete, delete-orphan",
    )

    @hybrid_property
    def is_active(self) -> bool:
        "Required by Flask-Login"
        return self.approved

    @property
    def total_time(self) -> timedelta:
        "Total time for all stamps"
        return self.yearly_time()

    def yearly_time(self, year: int | None = None) -> timedelta:
        "Total time for all stamps in a year"
        year = year or school_year_for_date(date.today())
        return sum(
            (s.elapsed for s in self.stamps if s.event.school_year == year),
            start=timedelta(),
        )

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

    def stamps_for(self, type_: EventType, year: int | None = None):
        "Get all stamps for an event type"
        year = year or school_year_for_date(date.today())
        return [
            s
            for s in self.stamps
            if s.event.type_ == type_ and s.event.school_year == year
        ]

    def total_stamps_for(self, type_: EventType, year: int | None = None) -> timedelta:
        "Total time for an event type"
        return sum(
            (s.elapsed for s in self.stamps_for(type_, year)),
            start=timedelta(),
        )

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

    def is_signed_into(self, ev: str | Event) -> bool:
        if isinstance(ev, str):
            ev = Event.get_from_code(ev)
        return bool(db.session.scalar(select(Active).filter_by(user=self, event=ev)))

    @property
    def total_funds(self) -> str:
        all_funds = [ev.raw_funds_for(self) for ev in db.session.scalars(select(Event))]
        money = sum(all_funds, start=0.0)
        return locale.currency(money)

    def yearly_funds(self, year: int | None = None) -> str:
        year = year or school_year_for_date(date.today())
        event_funds = [
            ev.raw_funds_for(self)
            for ev in db.session.scalars(select(Event).where(Event.school_year == year))
        ]
        money = sum(event_funds, start=0.0)
        return locale.currency(money)

    @staticmethod
    def get_visible_users() -> list[User]:
        return list(db.session.scalars(select(User).where(User.role.has(visible=True))))

    @staticmethod
    def make(
        email: str,
        name: str,
        password: str,
        role: Role | str,
        approved=False,
        subteam: Subteam | str = None,
        **kwargs,
    ) -> User:
        "Make a user, with password and hash"
        if "phone_number" in kwargs:
            kwargs["phone_number"] = normalize_phone_number_for_storage(
                kwargs["phone_number"]
            )

        if isinstance(role, str):
            role = Role.from_name(role)

        if isinstance(subteam, str):
            subteam = Subteam.from_name(subteam)

        user = User(
            email=email,
            name=name,
            password=generate_password_hash(password),
            role_id=role.id,
            subteam_id=subteam.id if subteam else None,
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
        guardian = User(
            name=name,
            email=email,
            role_id=role.id,
            phone_number=pn,
        )
        db.session.add(guardian)
        db.session.flush()
        return guardian

    @staticmethod
    def from_email(email: str) -> User | None:
        "Look up user by email"
        email = email.lower()
        return db.session.scalar(select(User).filter(func.lower(User.email) == email))

    @staticmethod
    def from_code(user_code: str) -> User | None:
        "Look up user by secret code"
        return db.session.scalar(select(User).filter_by(code=user_code))


class Guardian(db.Model):
    """
    This table is a bit strange as it has a one to one link with a User (Parent) as well as
    Many to Many links with User (Children).

    """

    __tablename__ = "guardians"
    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    contact_order: Mapped[int]

    # One to One: Links User to row in Guardian table
    user: Mapped[User] = db.relationship(back_populates="guardian_user_data")

    # Many to Many: Links Guardian to Children
    students: Mapped[list[Student]] = db.relationship(
        secondary=parent_child_association_table, back_populates="guardians"
    )

    @staticmethod
    def get_from(
        name: str, phone_number: str, email: str, contact_order: int
    ) -> Guardian:
        guardian_user = db.session.scalar(select(User).where(User.email == email))
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
    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))

    # Extra student information
    graduation_year: Mapped[int]

    # One to One: Links User to extra student information
    user: Mapped[User] = db.relationship(back_populates="student_user_data")

    # Many to Many: Links Student to Guardian
    guardians: Mapped[list[Guardian]] = db.relationship(
        secondary=parent_child_association_table, back_populates="students"
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
        email: str, name: str, password: str, graduation_year: int, **kwargs
    ) -> User:
        role = Role.from_name("student")
        student = User.make(
            name=name, email=email, password=password, role=role, **kwargs
        )
        student_user_data = Student(user_id=student.id, graduation_year=graduation_year)

        student.student_user_data = student_user_data
        db.session.add(student_user_data)
        return student


class Event(db.Model):
    __tablename__ = "events"
    id: Mapped[intpk]
    # User-visible name
    name: Mapped[str]
    # Description of the event
    description: Mapped[str] = mapped_column(default="")
    # Unique code for tracking
    code: Mapped[str] = mapped_column(unique=True, default=gen_code)
    # Location the event takes place at
    location: Mapped[str]
    # Start time
    start: Mapped[datetime]
    # End time
    end: Mapped[datetime]
    # Event type
    type_id: Mapped[int] = mapped_column(db.ForeignKey("event_types.id"))
    # Whether users can register for the event
    registration_open: Mapped[NonNullBool]

    # Total funds for event, in cents
    funds: Mapped[int] = mapped_column(default=0)
    # Total running cost for event, in cents
    cost: Mapped[int] = mapped_column(default=0)
    # Percentage of funds that go to the team
    overhead: Mapped[float] = mapped_column(default=0.3)

    stamps: Mapped[list[Stamps]] = db.relationship(
        back_populates="event", cascade="all, delete, delete-orphan"
    )
    active: Mapped[list[Active]] = db.relationship(
        back_populates="event", cascade="all, delete, delete-orphan"
    )
    type_: Mapped[EventType] = db.relationship(back_populates="events")
    blocks: Mapped[list[EventBlock]] = db.relationship(
        back_populates="event", cascade="all, delete, delete-orphan"
    )

    @staticmethod
    def get_from_code(event_code: str) -> Event | None:
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
        return (self.adjusted_start < now) & (now < self.adjusted_end)

    @is_active.expression
    def is_active(cls):
        "Usable in queries"
        if db.get_engine().name == "postgresql":
            pre_adj = cls.start - func.make_interval(
                0, 0, 0, 0, 0, current_app.config["PRE_EVENT_ACTIVE_TIME"]
            )
            post_adj = cls.end + func.make_interval(
                0, 0, 0, 0, 0, current_app.config["POST_EVENT_ACTIVE_TIME"]
            )
        elif db.get_engine().name == "sqlite":
            pre_adj = func.datetime(
                cls.start,
                f"-{current_app.config['PRE_EVENT_ACTIVE_TIME']} minutes",
            )
            post_adj = func.datetime(
                cls.end,
                f"+{current_app.config['POST_EVENT_ACTIVE_TIME']} minutes",
            )
        return and_((pre_adj < func.now()), (post_adj > func.now())).label("is_active")

    @hybrid_property
    def school_year(self) -> int:
        return school_year_for_date(self.adjusted_start.date())

    @school_year.expression
    def school_year(cls):
        "Usable in queries"
        if db.get_engine().name == "postgresql":
            adj_date = func.extract("year", cls.start + func.make_interval(0, 6))
        elif db.get_engine().name == "sqlite":
            adj_date = func.datetime(cls.start, "+6 months", "year")
        return adj_date.label("school_year")

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

    def scan(self, user: User) -> StampEvent:
        active: Active | None = db.session.scalar(
            select(Active).filter_by(user=user, event=self)
        )
        if active:
            stamp = active.convert_to_stamp()
            # Elapsed needs to be taken after committing to the DB
            # otherwise it won't be populated
            sign = f"out after {stamp.elapsed}"
            return StampEvent(user.human_readable, sign)
        else:
            self.sign_in(user)
            return StampEvent(user.human_readable, "in")

    def sign_in(self, user: User):
        active = Active(user=user, event=self)
        db.session.add(active)
        db.session.commit()

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


class EventType(db.Model):
    __tablename__ = "event_types"
    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str]
    autoload: Mapped[NonNullBool]

    events: Mapped[list[Event]] = db.relationship(back_populates="type_")

    @staticmethod
    def from_name(name: str) -> EventType:
        return db.session.scalar(select(EventType).filter_by(name=name))


class Active(db.Model):
    __tablename__ = "active"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(db.ForeignKey("events.id"))
    start: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = db.relationship()
    event: Mapped[Event] = db.relationship()

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

    def convert_to_stamp(self: Active, end: datetime | None = None):
        stamp = Stamps(
            user=self.user,
            event=self.event,
            start=self.start,
        )
        if end is not None:
            stamp.end = end
        db.session.delete(self)
        db.session.add(stamp)
        db.session.commit()
        return stamp


class Stamps(db.Model):
    __tablename__ = "stamps"
    id: Mapped[intpk]
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    event_id: Mapped[int] = mapped_column(db.ForeignKey("events.id"))
    start: Mapped[datetime]
    end: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = db.relationship(back_populates="stamps")
    event: Mapped[Event] = db.relationship(back_populates="stamps")

    @hybrid_property
    def elapsed(self) -> timedelta:
        "Elapsed time for a stamp"
        return self.end - self.start


class Role(db.Model):
    __tablename__ = "account_types"
    id: Mapped[intpk]
    name: Mapped[str]

    admin: Mapped[NonNullBool]
    mentor: Mapped[NonNullBool]
    guardian: Mapped[NonNullBool]
    can_display: Mapped[NonNullBool]
    autoload: Mapped[NonNullBool]
    can_see_subteam: Mapped[NonNullBool]
    visible: Mapped[bool] = mapped_column(default=True)
    receives_funds: Mapped[NonNullBool]

    users: Mapped[list[User]] = db.relationship(back_populates="role")

    @staticmethod
    def from_name(name) -> Role:
        "Get a role by name"
        return db.session.scalar(select(Role).filter_by(name=name))

    @staticmethod
    def get_visible() -> list[Role]:
        return db.session.scalars(select(Role).filter_by(visible=True))


class Subteam(db.Model):
    __tablename__ = "subteams"
    id: Mapped[intpk]
    name: Mapped[str]

    members: Mapped[list[User]] = db.relationship(back_populates="subteam")

    @staticmethod
    def from_name(name) -> Subteam:
        "Get a subteam by name"
        return db.session.scalar(select(Subteam).filter_by(name=name))


class EventRegistration(db.Model):
    __tablename__ = "eventregistrations"
    id: Mapped[intpk]

    # Link to event block
    event_block_id: Mapped[int] = mapped_column(db.ForeignKey("eventblocks.id"))
    event_block: Mapped[EventBlock] = db.relationship(back_populates="registrations")
    # Link to user
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    user: Mapped[User] = db.relationship()
    # User comment for event block
    comment: Mapped[str]

    registered: Mapped[NonNullBool]

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
    id: Mapped[intpk]

    # Start Time for block
    start: Mapped[datetime]
    # End time for block
    end: Mapped[datetime]
    # Link to Event
    event_id: Mapped[int] = mapped_column(db.ForeignKey("events.id"))
    event: Mapped[Event] = db.relationship(back_populates="blocks")

    registrations: Mapped[list[EventRegistration]] = db.relationship(
        back_populates="event_block", cascade="all, delete, delete-orphan"
    )

    @property
    def start_local(self) -> str:
        "Start time in local time zone"
        return correct_time_from_storage(self.start).strftime("%c")

    @property
    def end_local(self) -> str:
        "End time in local time zone"
        return correct_time_from_storage(self.end).strftime("%c")
