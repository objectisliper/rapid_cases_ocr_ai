"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Web service main definitions

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
from flask import Flask
from flask_restful import Resource, Api


app = Flask(__name__)
app.config.from_pyfile('config.py')

api = Api(app)

from .views import *
