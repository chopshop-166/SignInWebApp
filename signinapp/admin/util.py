#!/usr/bin/env python

from functools import wraps

from flask import Blueprint, current_app, request
from flask_login import current_user
from flask_login.config import EXEMPT_METHODS

admin = Blueprint("admin", __name__)


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method in EXEMPT_METHODS or \
                current_app.config.get('LOGIN_DISABLED'):
            pass
        elif not current_user.is_authenticated or not current_user.admin:
            return current_app.login_manager.unauthorized()
        try:
            # current_app.ensure_sync available in Flask >= 2.0
            return current_app.ensure_sync(func)(*args, **kwargs)
        except AttributeError:
            return func(*args, **kwargs)
    return decorated_view
