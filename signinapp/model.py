#!/usr/bin/env python

from __future__ import annotations

import base64
import dataclasses
import hashlib
import re
from datetime import datetime
from typing import Tuple

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import relationship

from . import app

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")

HASH_RE = re.compile(
    r"^(?:[A-Za-z\d+/]{4})*(?:[A-Za-z\d+/]{3}=|[A-Za-z\d+/]{2}==)?$")


#db_name = 'signin.db'
db_name = ':memory:'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy(app)


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


class Person(db.Model):
    __tablename__ = "people"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    code = db.Column(db.String, nullable=False, unique=True)
    mentor = db.Column(db.Boolean, nullable=False)

    stamps = relationship("Stamps", back_populates="person")

    @hybrid_method
    def human_readable(self) -> str:
        return f"{'*' if self.mentor else ''}{self.name}"

    @classmethod
    def make(cls, name, mentor=False):
        the_hash = mk_hash(name)
        return Person(name=name, code=the_hash, mentor=mentor)


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

    stamps = relationship("Stamps", back_populates="event")


class Active(db.Model):
    __tablename__ = "active"
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("people.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    start = db.Column(db.DateTime, server_default=func.now())

    person = relationship("Person")
    event = relationship("Event")


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


class SqliteModel():
    def __init__(self) -> None:
        db.create_all()
        p = Person.make("Matt Soucy", mentor=True)
        db.session.add(p)
        db.session.commit()

    def get_name_stamps(self, name):
        m = NAME_RE.match(name)
        if not m:
            return []
        return Stamps.query.filter(Stamps.person.matches(m)).all()

    def get_event_stamps(self, event):
        return Stamps.query.filter(Stamps.event.code == event).all()

    def get_all_stamps(self):
        return [s.as_dict() for s in Stamps.query.all()]

    def get_active(self, event) -> list[Tuple[str, datetime]]:
        return [(active.person.human_readable(), active.start)
                for active in Active.query.join(Event).filter(Event.code == event).all()]

    def get_all_active(self) -> list[Tuple[str, datetime, str]]:
        return [(active.person.human_readable(), active.start, active.event.code)
                for active in Active.query.all()]

    def scan(self, event, name) -> StampEvent:
        code = canonical_name(name)
        if not code:
            return

        person = Person.query.filter(Person.code == code).first()
        if not person:
            return

        ev = Event.query.filter(Event.code == event).one_or_none()
        if not ev:
            ev = Event(name=event, code=event)
            db.session.add(ev)
            db.session.commit()

        active = Active.query.join(Person).filter(
            Person.code == code).one_or_none()
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
