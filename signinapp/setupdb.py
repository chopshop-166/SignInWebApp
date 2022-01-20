# Entry point for the application.
from .model import db

db.create_all()
