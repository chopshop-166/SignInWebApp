#!/usr/bin/env python

from flask_bootstrap import Bootstrap5
from flask import Flask

app = Flask(__name__)
bootstrap = Bootstrap5(app)