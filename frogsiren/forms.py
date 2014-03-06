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
    start_station = TextField("Start Station")
    end_station = TextField("End Station")
    sumbit = SubmitField("Add Route")

