#!/usr/bin/env python

from __future__ import annotations

import base64
import dataclasses
import hashlib
import re
from datetime import datetime
from typing import Tuple

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy()

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")

HASH_RE = re.compile(
    r"^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$")


def mk_hash(name: str):
    return base64.b64encode(name.lower().encode("utf-8")).decode("utf-8")


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
    mentor = db.Column(db.Boolean, nullable=False)

    stamps = relationship("Stamps", back_populates="person")

    @hybrid_method
    def human_readable(self) -> str:
        return f"{'*' if self.mentor else ''}{self.name}"

    @classmethod
    def make(cls, name, password, mentor=False):
        the_hash = mk_hash(name)
        return Person(name=name, password=generate_password_hash(password),
                      code=the_hash, mentor=mentor)

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
    code = db.Column(db.String)
    # Location the event takes place at
    location = db.Column(db.String)
    # Start time
    start = db.Column(db.DateTime)
    # End time
    end = db.Column(db.DateTime)
    # Event type
    type_ = db.Column(db.String)

    stamps = relationship("Stamps", back_populates="event")
    active = relationship("Active", back_populates="event")


class Active(db.Model):
    __tablename__ = "active"
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    person = relationship("Person")
    event = relationship("Event")

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


class SqliteModel():

    def get_stamps(self, name=None, event=None):
        query = Stamps.query
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

    def export(self, name: str = None,
               start: datetime = None, end: datetime = None,
               type_: str = None, headers=True) -> list[list[str]]:
        query = Stamps.query
        if name:
            code = mk_hash(name)
            query = query.join(Person).filter_by(code=code)
        if start:
            query = query.filter(Stamps.start < start)
        if end:
            query = query.filter(Stamps.end > end)
        if type_:
            query = query.join(Event).filter_by(type_=type_)
        result = [stamp.as_list() for stamp in query.all()]
        if headers:
            result = [["Name", "Start", "End", "Elapsed", "Event"]] + result
        return result

    def scan(self, event, name) -> StampEvent:
        code = canonical_name(name)
        if not code:
            return

        person = Person.query.filter_by(code=code).one_or_none()
        if not person:
            return

        ev = Event.query.filter_by(code=event).one_or_none()
        if not ev:
            ev = Event(name=event, code=event)
            db.session.add(ev)
            db.session.commit()

        active = Active.query.join(Person).filter_by(code=code).one_or_none()
        if active:
            stamp = Stamps(person=person, event=ev, start=active.start)
            db.session.delete(active)
            db.session.add(stamp)
            db.session.commit()
            # Elapsed needs to be taken after committing to the DB
            # otherwise it won't be populated
            sign = f"out after {stamp.elapsed}"
            return StampEvent(person.human_readable(), sign)
        else:
            active = Active(person=person, event=ev)
            db.session.add(active)
            db.session.commit()
            return StampEvent(person.human_readable(), "in")


model = SqliteModel()
