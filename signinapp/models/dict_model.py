#!/usr/bin/env python

from __future__ import annotations

from collections import defaultdict
import dataclasses
from datetime import datetime
from itertools import chain
import re
from typing import DefaultDict, Dict, List, Tuple

from .base import Model, NAME_RE

@dataclasses.dataclass(frozen=True)
class Config():
    first : str
    last : str
    mentor : bool = False

    def human_readable(self) -> str:
        result = f"{self.first} {self.last}"
        if self.mentor:
            result += " (mentor)"
        return result

    def __hash__(self) -> int:
        return hash((self.first.lower(), self.last.lower(), self.mentor))

    def sortkey(self) -> Tuple[bool, str, str]:
        return (self.mentor, self.first, self.last)
    
    @classmethod
    def make_from(cls, text) -> Config:
        m = NAME_RE.match(text)
        return Config(m['first'], m['last'], m['mentor'])

class DictModel(Model):
    def __init__(self) -> None:
        self.signed_in : DefaultDict[str, Dict[Config, datetime]] = defaultdict(dict)
    
    def get(self, event) -> List[Tuple[str, datetime]]:
        # Get key-value pairs
        items = self.signed_in[event].items()
        # Sort mentors first then students
        items = sorted(items, key=lambda x: x[0].sortkey())
        # Convert to human readable format
        items = [(k.human_readable(), v) for k,v in items]
        return items
    
    def get_all(self) -> List[Tuple[str, datetime, str]]:
        # Get key-value pairs
        items = chain.from_iterable([(k,v,ev) for k,v in e.items()]
                                    for ev,e in self.signed_in.items())
        # Sort mentors first then students
        items = sorted(items, key=lambda x: x[0].sortkey())
        # Convert to human readable format
        items = [(k.human_readable(), v, e) for k,v,e in items]
        return items
    
    def scan(self, event, name) -> Tuple[str, str]:
        c = Config.make_from(name)
        sign = "in"
        if c in self.signed_in[event]:
            starttime = self.signed_in[event][c]
            del self.signed_in[event][c]
            elapsed_time = datetime.now() - starttime
            sign = f"out after {elapsed_time}"
        else:
            self.signed_in[event][c] = datetime.now()
        return c.human_readable(), sign