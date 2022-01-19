# Entry point for the application.
from .models.sqlite_model import db

db.create_all()
