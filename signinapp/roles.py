from functools import wraps

from flask import current_app, redirect, request, url_for
from flask_login import current_user
from flask_login.config import EXEMPT_METHODS
from flask_rbac import RBAC

# Only thing in this file so that we can import it
rbac = RBAC()
