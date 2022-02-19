#!/usr/bin/env python

from __future__ import annotations

import base64
import dataclasses
import datetime
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy()

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")

HASH_RE = re.compile(
    r"^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$")


LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo


def mk_hash(name: str):
    'Make a user hash'
    return base64.b64encode(name.lower().encode("utf-8")).decode("utf-8")


def event_code():
    'Generate an event code'
    return secrets.token_urlsafe(16)


def canonical_name(name: str):
    'Attempt to get a user string'
    if m := HASH_RE.match(name):
        return name
    if m := NAME_RE.match(name):
        return mk_hash(f"{m['first']} {m['last']}")


@dataclasses.dataclass
class StampEvent():
    name: str
    event: str


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String)
    code = db.Column(db.String, nullable=False, unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("account_types.id"))
    subteam_id = db.Column(db.Integer, db.ForeignKey("subteams.id"))
    approved = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    stamps = relationship("Stamps", back_populates="user")
    role = relationship("Role")
    subteam = relationship("Subteam", back_populates="members")
    awards = relationship("BadgeAward", back_populates="owner")

    @hybrid_property
    def is_active(self) -> bool:
        ' Required by Flask-Login '
        return self.active & self.approved

    @hybrid_property
    def total_time(self) -> timedelta:
        ' Total time for all stamps '
        return sum((s.elapsed for s in self.stamps), start=timedelta())

    @hybrid_property
    def badges(self) -> list[BadgeAward]:
        ' The badges associated with this user '
        return BadgeAward.query.filter_by(user_id=self.id).all()

    @hybrid_method
    def has_badge(self, badge_id: int) -> bool:
        ' Test if a badge is assigned to a user '
        return badge_id in [b.badge_id for b in self.badges]

    @hybrid_method
    def award_badge(self, badge_id: int):
        ' Assign a badge to a user '
        if not self.has_badge(badge_id):
            award = BadgeAward(badge_id=badge_id, owner=self)
            db.session.add(award)
            db.session.commit()

    @hybrid_method
    def remove_badge(self, badge_id: int):
        ' Remove a badge from a user '
        if self.has_badge(badge_id):
            award = BadgeAward.query.filter_by(
                badge_id=badge_id, owner=self).one_or_none()
            db.session.delete(award)
            db.session.commit()

    @hybrid_method
    def stamps_for(self, type_: EventType):
        ' Get all stamps for an event type '
        return [s for s in self.stamps
                if (s.event.type_ == type_) & s.event.enabled]

    @hybrid_method
    def total_stamps_for(self, type_: EventType) -> timedelta:
        ' Total time for an event type '
        return sum((s.elapsed for s in self.stamps_for(type_)),
                   start=timedelta())

    @hybrid_method
    def can_view(self, user: User):
        ' Whether the user in question can view this user '
        return self.role.mentor or self.role.admin or self == user

    @hybrid_method
    def human_readable(self) -> str:
        ' Human readable string for display on a web page '
        return f"{'*' if self.role.mentor else ''}{self.name}"

    @staticmethod
    def make(name: str, password: str, role: Role,
             subteam: Subteam = None, approved=False) -> User:
        ' Make a user, with password and hash '
        return User(name=name, password=generate_password_hash(password),
                    code=mk_hash(name), role_id=role.id, subteam=subteam,
                    approved=approved)

    @staticmethod
    def get_canonical(name) -> User | None:
        ' Look up user by name '
        code = mk_hash(name)
        return User.query.filter_by(code=code).one_or_none()


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    # User-visible name
    name = db.Column(db.String)
    # Description of the event
    description = db.Column(db.String)
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

    stamps = relationship("Stamps", back_populates="event")
    active = relationship("Active", back_populates="event")
    type_ = relationship("EventType", back_populates="events")

    @hybrid_property
    def start_local(self) -> str:
        ' Start time in local time zone '
        return self.start.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_property
    def end_local(self) -> str:
        ' End time in local time zone '
        return self.end.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_property
    def is_active(self) -> bool:
        ' Test for if the event is currently active '
        now = datetime.now()
        return (self.enabled &
                (self.start < now) &
                (now < self.end))

    @is_active.expression
    def is_active(cls):
        ' Usable in queries '
        return and_(cls.enabled,
                    (cls.start < func.now()),
                    (func.now() < cls.end))

    def scan(self, name) -> StampEvent:
        if not self.is_active:
            return

        code = canonical_name(name)
        if not code:
            return

        user = User.query.filter_by(code=code).one_or_none()
        if not (user and user.approved):
            return

        active = Active.query.filter_by(event=self).join(
            User).filter_by(code=code).one_or_none()
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

    events = relationship("Event", back_populates="type_")


class Active(db.Model):
    __tablename__ = "active"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    user = relationship("User")
    event = relationship("Event")

    @hybrid_property
    def start_local(self) -> str:
        ' Start time in local time zone '
        return self.start.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_method
    def as_dict(self):
        ' Return a dictionary for sending to the web page '
        return {
            "user": self.user.human_readable(),
            "start": self.start,
            "event": self.event.name
        }

    @staticmethod
    def get(event=None) -> list[dict]:
        query = Active.query
        if event:
            query = query.join(Event).filter(Event.code == event)
        return [active.as_dict() for active in query.all()]


class Stamps(db.Model):
    __tablename__ = "stamps"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("users.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime, server_default=func.now())

    user = relationship("User", back_populates="stamps")
    event = relationship("Event", back_populates="stamps")

    @hybrid_property
    def elapsed(self) -> timedelta:
        ' Elapsed time for a stamp '
        return self.end - self.start

    @hybrid_method
    def as_dict(self):
        ' Return a dictionary for sending to the web page '
        return {
            "user": self.user.human_readable(),
            "elapsed": str(self.elapsed),
            "start": self.start,
            "end": self.end,
            "event": self.event.name
        }

    @hybrid_method
    def as_list(self):
        ' Return a list for sending to the web page '
        return [self.user.human_readable(),
                self.start, self.end,
                self.elapsed,
                self.event.name, self.event.type_.name]

    @staticmethod
    def get(name=None, event=None):
        ' Get stamps matching a requirement '
        query = Stamps.query.join(Event).filter_by(enabled=True)
        if event:
            query = query.filter_by(code=event)
        if name:
            code = canonical_name(name)
            query = query.join(User).filter_by(code=code)
        return [s.as_dict() for s in query.all()]

    @staticmethod
    def export(name: str = None,
               start: datetime = None,
               end: datetime = None,
               type_: str = None,
               subteam: Subteam = None,
               headers=True) -> list[list[str]]:
        query = Stamps.query.join(Event).filter_by(enabled=True)
        if name:
            code = mk_hash(name)
            query = query.join(User).filter_by(code=code)
        if start:
            query = query.filter(Stamps.start < start)
        if end:
            query = query.filter(Stamps.end > end)
        if type_:
            query = query.join(Event).filter_by(type_=type_)
        if subteam:
            query = query.join(User).filter_by(subteam=subteam)
        result = [stamp.as_list() for stamp in query.all()]
        if headers:
            result = [["Name", "Start", "End", "Elapsed", "Event", "Event Type"]] + result
        return result


class Role(db.Model):
    __tablename__ = "account_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    mentor = db.Column(db.Boolean, nullable=False, default=False)
    can_display = db.Column(db.Boolean, nullable=False, default=False)
    autoload = db.Column(db.Boolean, nullable=False, default=False)
    can_see_subteam = db.Column(db.Boolean, nullable=False, default=False)

    @classmethod
    def from_name(cls, name) -> Role:
        ' Get a role by name '
        return cls.query.filter_by(name=name).one_or_none()


class Subteam(db.Model):
    __tablename__ = "subteams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    members = relationship("User", back_populates="subteam")

    @classmethod
    def from_name(cls, name) -> Subteam:
        ' Get a subteam by name '
        return cls.query.filter_by(name=name).one_or_none()


class Badge(db.Model):
    ' Represents an "achievement", accomplishment, or certification '
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    icon = db.Column(db.String)
    color = db.Column(db.String, default="black")

    awards = relationship("BadgeAward", back_populates="badge")


class BadgeAward(db.Model):
    ' Represents a pairing of user to badge, with received date '
    __tablename__ = "badge_awards"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id"))
    received = db.Column(db.DateTime, server_default=func.now())

    owner = relationship("User", uselist=False)
    badge = relationship("Badge", back_populates="awards")
