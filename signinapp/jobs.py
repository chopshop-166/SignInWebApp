from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from flask_apscheduler import APScheduler
from flask import current_app
from sqlalchemy.future import select

from .model import Active, create_stamp_from_active, db

# initialize scheduler
scheduler = APScheduler()


@scheduler.task("interval", id="UserSignOutJob", seconds=30)
def EventEndJob():
    """
    This monitor checks all of the entries in the active table
        For each entry check if the adjusted end time has passed
    """
    with scheduler.app.app_context():
        time = datetime.now(tz=ZoneInfo(current_app.config["TIME_ZONE"]))
        active_entries: List[Active] = db.session.scalars(select(Active))

        for active in active_entries:
            if active.event.adjusted_end < time:
                if current_app.config["AUTO_SIGNOUT_BEHAVIOR"] == "Credit":
                    # Expire the active session
                    create_stamp_from_active(active, active.event.end)
                elif current_app.config["AUTO_SIGNOUT_BEHAVIOR"] == "Discard":
                    # Delete active entry without crediting the user
                    db.session.delete(active)
        db.session.commit()
