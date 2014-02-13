from flask.ext.sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class Stations(db.Model):
    stationID = db.Column(db.Integer, unique=True, primary_key=True)
    stationName = db.Column(db.Text, unique=False)
    systemID = db.Column(db.Integer, unique=False)

class Contract(db.Model):
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


if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'
    db.init_app(app)
    with app.test_request_context():
        db.drop_all(app=app)
        db.create_all(app=app)
        station = Stations(stationID=60003478,systemID=30005055, stationName="Zinkon VII - Moon 1 - Caldari Business Tribunal Accounting")
        db.session.add(station)
        station = Stations(stationID=60003760, systemID=30000142, stationName="Jita IV - Moon 4 - Caldari Navy Assembly Plant")
        db.session.add(station)
        station = Stations(stationID=60013159, systemID=30004299, stationName="Sakht VI - Moon 7 - Genolution Biotech Production")
        db.session.add(station)
        db.session.commit()
    exit(0)

