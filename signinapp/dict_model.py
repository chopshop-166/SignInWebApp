#!/usr/bin/env python

from collections import defaultdict
import dataclasses
from datetime import datetime
import re
from typing import DefaultDict, Dict, List, Tuple

NAME_RE = re.compile(r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")

@dataclasses.dataclass(frozen=True)
class Config():
    first : str
    last : str
    mentor : bool = False

    def human_readable(self):
        result = f"{self.first} {self.last}"
        if self.mentor:
            result += " (mentor)"
        return result

    def userid(self):
        return hash(Config(self.first.lower(), self.last.lower(), self.mentor))

    def sortkey(self):
        return (self.mentor, self.first, self.last)

def str2config(text : str):
    m = NAME_RE.match(text)
    return Config(m['first'], m['last'], m['mentor'])

class DictModel():
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
    
    def scan(self, event, name) -> Tuple[str, str]:
        c = str2config(name)
        sign = "in"
        if c in self.signed_in[event]:
            starttime = self.signed_in[event][c]
            del self.signed_in[event][c]
            elapsed_time = datetime.now() - starttime
            sign = f"out after {elapsed_time}"
        else:
            self.signed_in[event][c] = datetime.now()
        return c.human_readable(), sign