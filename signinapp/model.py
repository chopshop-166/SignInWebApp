#!/usr/bin/env python

from __future__ import annotations

import base64
import dataclasses
import datetime
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
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
    return base64.b64encode(name.lower().encode("utf-8")).decode("utf-8")


def event_code():
    return secrets.token_urlsafe(16)


def canonical_name(name: str):
    if m := NAME_RE.match(name):
        return mk_hash(f"{m['first']} {m['last']}")
    if m := HASH_RE.match(name):
        return name


@dataclasses.dataclass
class StampEvent():
    name: str
    event: str


class Person(UserMixin, db.Model):
    __tablename__ = "people"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String)
    code = db.Column(db.String, nullable=False, unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("account_types.id"))
    subteam_id = db.Column(db.Integer, db.ForeignKey("subteams.id"))

    stamps = relationship("Stamps", back_populates="person")
    role = relationship("Role")
    subteam = relationship("Subteam", back_populates="members")

    @hybrid_property
    def mentor(self):
        return self.role.mentor

    @hybrid_property
    def can_display(self):
        return self.role.can_display

    @hybrid_property
    def admin(self):
        return self.role.admin

    @hybrid_property
    def total_time(self) -> timedelta:
        return sum((s.elapsed for s in self.stamps), start=timedelta())

    @hybrid_method
    def stamps_for(self, type_: EventType):
        return [s for s in self.stamps
                if s.event.type_ == type_
                and s.event.enabled]

    @hybrid_method
    def total_stamps_for(self, type_: EventType) -> timedelta:
        return sum((s.elapsed for s in self.stamps_for(type_)),
                   start=timedelta())

    @hybrid_method
    def can_view(self, user: Person):
        return self.mentor or self.admin or current_user is user

    @hybrid_method
    def human_readable(self) -> str:
        return f"{'*' if self.mentor else ''}{self.name}"

    @classmethod
    def make(cls, name: str, password: str, role: Role, subteam: Subteam = None):
        the_hash = mk_hash(name)
        return Person(name=name, password=generate_password_hash(password),
                      code=the_hash, role_id=role.id, subteam=subteam)

    @classmethod
    def get_canonical(cls, name):
        code = mk_hash(name)
        return Person.query.filter_by(code=code).one_or_none()


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
        return self.start.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_property
    def end_local(self) -> str:
        return self.end.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_property
    def is_active(self) -> bool:
        now = datetime.now()
        return (self.enabled == True and
                self.start < now and
                now < self.end)


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
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    person = relationship("Person")
    event = relationship("Event")

    @hybrid_property
    def start_local(self) -> str:
        return self.start.astimezone(LOCAL_TIMEZONE).strftime("%c")

    @hybrid_method
    def as_dict(self):
        return {
            "person": self.person.human_readable(),
            "start": self.start,
            "event": self.event.name
        }


class Stamps(db.Model):
    __tablename__ = "stamps"
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.String, db.ForeignKey("people.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime, server_default=func.now())

    person = relationship("Person", back_populates="stamps")
    event = relationship("Event", back_populates="stamps")

    @hybrid_property
    def elapsed(self):
        return self.end - self.start

    @hybrid_method
    def as_dict(self):
        return {
            "person": self.person.human_readable(),
            "elapsed": str(self.elapsed),
            "start": self.start,
            "end": self.end,
            "event": self.event.name
        }

    @hybrid_method
    def as_list(self):
        return [self.person.human_readable(),
                self.start, self.end,
                self.elapsed, self.event.name]


class Role(db.Model):
    __tablename__ = "account_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    mentor = db.Column(db.Boolean, nullable=False, default=False)
    can_display = db.Column(db.Boolean, nullable=False, default=False)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    autoload = db.Column(db.Boolean, nullable=False, default=False)
    can_see_subteam = db.Column(db.Boolean, nullable=False, default=False)

    @classmethod
    def from_name(cls, name):
        return cls.query.filter_by(name=name).one_or_none()


class Subteam(db.Model):
    __tablename__ = "subteams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    members = relationship("Person", back_populates="subteam")


class SqliteModel():

    def get_stamps(self, name=None, event=None):
        query = Stamps.query.filter(Stamps.event.enabled == True)
        if name:
            code = canonical_name(name)
            query = query.join(Person).filter_by(code=code)
        if event:
            query = query.join(Event).filter_by(code=event)
        return [s.as_dict() for s in query.all()]

    def get_active(self, event=None) -> list[dict]:
        query = Active.query
        if event:
            query = query.join(Event).filter(Event.code == event)
        return [active.as_dict() for active in query.all()]

    def export(self,
               name: str = None,
               start: datetime = None,
               end: datetime = None,
               type_: str = None,
               subteam: Subteam = None,
               headers=True) -> list[list[str]]:
        query = Stamps.query.filter(Stamps.event.enabled == True)
        if name:
            code = mk_hash(name)
            query = query.join(Person).filter_by(code=code)
        if start:
            query = query.filter(Stamps.start < start)
        if end:
            query = query.filter(Stamps.end > end)
        if type_:
            query = query.join(Event).filter_by(type_=type_)
        if subteam:
            query = query.join(Person).filter_by(subteam=subteam)
        result = [stamp.as_list() for stamp in query.all()]
        if headers:
            result = [["Name", "Start", "End", "Elapsed", "Event"]] + result
        return result

    def scan(self, ev, name) -> StampEvent:
        if not (ev and ev.is_active):
            return

        code = canonical_name(name)
        if not code:
            return

        person = Person.query.filter_by(code=code).one_or_none()
        if not person:
            return

        active = Active.query.join(Person).filter_by(code=code).one_or_none()
        if not active:
            active = Active(person=person, event=ev)
            db.session.add(active)
            db.session.commit()
            return StampEvent(person.human_readable(), "in")

        stamp = Stamps(person=person, event=ev, start=active.start)
        db.session.delete(active)
        db.session.add(stamp)
        db.session.commit()
        # Elapsed needs to be taken after committing to the DB
        # otherwise it won't be populated
        sign = f"out after {stamp.elapsed}"
        return StampEvent(person.human_readable(), sign)


model = SqliteModel()
