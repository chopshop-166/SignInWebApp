#!/usr/bin/env python

from __future__ import annotations

import abc
import dataclasses
import re
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict, Dict, List, Tuple

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import relationship

from . import app

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")

#db_name = 'signin.db'
db_name = ':memory:'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy(app)


class Person(db.Model):
    __tablename__ = "people"
    id = db.Column(db.Integer, primary_key=True)
    first = db.Column(db.String, nullable=False)
    last = db.Column(db.String, nullable=False)
    mentor = db.Column(db.Boolean, nullable=False)

    stamps = relationship("Stamps", back_populates="person")

    @hybrid_method
    def human_readable(self) -> str:
        return f"{'*' if self.mentor else ''}{self.first} {self.last}"

    @hybrid_method
    def matches(self, other: re.Match) -> bool:
        return ((func.lower(self.first) == other["first"].lower()) &
                (func.lower(self.last) == other["last"].lower()) &
                (self.mentor == bool(other["mentor"])))

    @classmethod
    def make_from(cls, text) -> Person:
        m = NAME_RE.match(text)
        if m is not None:
            return Person(first=m['first'], last=m['last'], mentor=bool(m['mentor']))


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

    def get_name_stamps(self, name):
        m = NAME_RE.match(name)
        if not m:
            return []
        return Stamps.query.filter(Stamps.person.matches(m)).all()

    def get_event_stamps(self, event):
        return Stamps.query.filter(Stamps.event.code == event).all()

    def get_all_stamps(self):
        return [s.as_dict() for s in Stamps.query.all()]

    def get_active(self, event) -> List[Tuple[str, datetime]]:
        return [(active.person.human_readable(), active.start)
                for active in Active.query.join(Event).filter(Event.code == event).all()]

    def get_all_active(self) -> List[Tuple[str, datetime, str]]:
        return [(active.person.human_readable(), active.start, active.event.code)
                for active in Active.query.all()]

    def scan(self, event, name) -> Tuple[str, str]:
        m = NAME_RE.match(name)
        if not m:
            return ("", "")

        person = Person.query.filter(Person.matches(m)).first()
        if not person:
            person = Person.make_from(name)
            db.session.add(person)
            db.session.commit()

        ev = Event.query.filter(Event.code == event).one_or_none()
        if not ev:
            ev = Event(name=event, code=event)
            db.session.add(ev)
            db.session.commit()

        active = Active.query.join(Person).filter(
            Person.matches(m)).one_or_none()
        if active:
            stamp = Stamps(person=person, event=ev, start=active.start)
            db.session.delete(active)
            db.session.add(stamp)
            db.session.commit()
            # Elapsed needs to be taken after committing to the DB
            # otherwise it won't be populated
            sign = f"out after {stamp.elapsed}"
            return (person.human_readable(), sign)
        else:
            active = Active(person=person, event=ev)
            db.session.add(active)
            db.session.commit()
            return (person.human_readable(), "in")
