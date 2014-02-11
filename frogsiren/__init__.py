
from flask import Flask

app = Flask(__name__)

app.secret_key = "Some key used for creating hidden tags"

import frogsiren.routes


