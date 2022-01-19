#!/usr/bin/env python

import abc
from collections import defaultdict
import dataclasses
from datetime import datetime
import re
from typing import DefaultDict, Dict, List, Tuple

NAME_RE = re.compile(
    r"^(?P<mentor>(?i)mentor[ -]*)?(?P<last>[a-zA-Z ']+),\s*(?P<first>[a-zA-Z ']+)$")


class Model(abc.ABC):

    @abc.abstractmethod
    def get_active(self, event) -> List[Tuple[str, datetime]]:
        pass

    @abc.abstractmethod
    def get_all_active(self, event) -> List[Tuple[str, datetime, str]]:
        pass

    @abc.abstractmethod
    def scan(self, event, name) -> Tuple[str, str]:
        pass
