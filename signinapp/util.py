import string
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app
from wtforms import SelectMultipleField, widgets


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def correct_time_for_storage(time: datetime) -> datetime:
    # Check if datetime has a tz already:
    if time.tzinfo is None:
        # If not, set TZ to ET
        time = time.replace(tzinfo=ZoneInfo(current_app.config["TIME_ZONE"]))
    return time.astimezone(timezone.utc)


def correct_time_from_storage(time: datetime) -> datetime:
    # Check if datetime has a tz already:
    if time.tzinfo is None:
        # If not, set TZ to ET
        time = time.replace(tzinfo=timezone.utc)
    return time.astimezone(ZoneInfo(current_app.config["TIME_ZONE"]))


def normalize_phone_number_for_storage(number: str):
    """Remove all extra whitespace and characters from a phone number"""
    return "".join(c for c in (number or "").strip() if c in string.digits)


def normalize_phone_number_from_storage(number: str):
    """Format the phone number for display"""
    return f"({number[0:3]}) {number[3:6]}-{number[6:10]}" if number else ""


def generate_grade_choices():
    today = date.today()
    this_grad_year = today.year
    # If it's past June then graduation is a year from now
    if today.month > 6:
        this_grad_year += 1

    return {
        this_grad_year + 3: f"Freshman ({this_grad_year+3})",
        this_grad_year + 2: f"Sophomore ({this_grad_year+2})",
        this_grad_year + 1: f"Junior ({this_grad_year+1})",
        this_grad_year: f"Senior ({this_grad_year})",
    }
