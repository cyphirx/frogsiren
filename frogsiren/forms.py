from flask.ext.wtf import Form
from wtforms import TextField,validators, PasswordField, SubmitField


class SigninForm(Form):
  name = TextField("Username",  [validators.Required("Please enter your email address."), validators.Email("Please enter your email address.")])
  password = PasswordField('Password', [validators.Required("Please enter a password.")])
  submit = SubmitField("Sign In")
  uid = 0

  def __init__(self, *args, **kwargs):
    Form.__init__(self, *args, **kwargs)


class RoutesForm(Form):
    start_station_id = TextField("Start Station ID")
    end_station_id = TextField("End Station ID")
    cost = TextField("Cost")
    submit = SubmitField("Add Route")

class StationForm(Form):
    station_id = TextField("Station ID")
    station_name = TextField("Station Name")
    system_id = TextField("System ID")
    submit = SubmitField("Add A Station")
