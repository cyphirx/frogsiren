from flask.ext.sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class Stations(db.Model):
    __tablename__ = 'stations'
    stationID = db.Column(db.Integer, unique=True, primary_key=True)
    stationName = db.Column(db.Text, unique=False)


class Contract(db.Model):
    __tablename__ = 'contracts'
    contractID = db.Column(db.BigInteger, unique=True, primary_key=True)
    issuerID = db.Column(db.BigInteger, unique=False)
    issuerCorpID = db.Column(db.BigInteger, unique=False)
    assigneeID = db.Column(db.BigInteger, unique=False)
    acceptorID = db.Column(db.BigInteger, unique=False)
    startStationID = db.Column(db.Integer, unique=False)
    endStationID = db.Column(db.Integer, unique=False)
    type = db.Column(db.Text, unique=False)
    status = db.Column(db.Text, unique=False)
    title = db.Column(db.Text, unique=False)
    forCorp = db.Column(db.Integer, unique=False)
    availability = db.Column(db.Text, unique=False)
    dateIssued = db.Column(db.DateTime, unique=False)
    dateExpired = db.Column(db.DateTime, unique=False)
    dateAccepted = db.Column(db.DateTime, unique=False)
    numDays = db.Column(db.Integer, unique=False)
    dateCompleted = db.Column(db.DateTime, unique=False)
    price = db.Column(db.Float, unique=False)
    reward = db.Column(db.Float, unique=False)
    collateral = db.Column(db.Float, unique=False)
    buyout = db.Column(db.Float, unique=False)
    volume = db.Column(db.Float, unique=False)

