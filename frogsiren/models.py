from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class Stations(db.Model):
    stationID = db.Column(db.Integer, unique=True, primary_key=True)
    stationName = db.Column(db.Text, unique=False)
    systemID = db.Column(db.Integer, unique=False)


class Routes(db.Model):
    route_id = db.Column(db.Integer, primary_key=True)
    start_station = db.Column(db.Integer, unique=False)
    end_station = db.Column(db.Integer, unique=False)
    cost = db.Column(db.Integer, unique=False)
    status = db.Column(db.Boolean, unique=False)


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
    dateIssued = db.Column(db.Text, unique=False)
    dateExpired = db.Column(db.Text, unique=False, nullable=True)
    dateAccepted = db.Column(db.Text, unique=False, nullable=True)
    numDays = db.Column(db.Integer, unique=False)
    dateCompleted = db.Column(db.Text, unique=False, nullable=True)
    price = db.Column(db.Float, unique=False)
    reward = db.Column(db.Float, unique=False)
    collateral = db.Column(db.Float, unique=False)
    buyout = db.Column(db.Float, unique=False)
    volume = db.Column(db.Float, unique=False)
    cached = db.Column(db.Text, unique=False)


def initial_db():
    from flask import Flask
    from sqlalchemy import exists

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cache.db'
    db.init_app(app)
    with app.test_request_context():
        db.create_all(app=app)
        if not db.session.query(exists().where(Stations.stationID == 60003478)).scalar():
            station = Stations(stationID=60003478, systemID=30005055,
                               stationName="Zinkon VII - Moon 1 - Caldari Business Tribunal Accounting")
            db.session.add(station)
        if not db.session.query(exists().where(Stations.stationID == 60003760)).scalar():
            station = Stations(stationID=60003760, systemID=30000142,
                               stationName="Jita IV - Moon 4 - Caldari Navy Assembly Plant")
            db.session.add(station)
        if not db.session.query(exists().where(Stations.stationID == 60013159)).scalar():
            station = Stations(stationID=60013159, systemID=30004299,
                               stationName="Sakht VI - Moon 7 - Genolution Biotech Production")
            db.session.add(station)
        if not db.session.query(exists().where(Stations.stationID == 60008494)).scalar():
            station = Stations(stationID=60008494, systemID=30002187,
                               stationName="Amarr VIII (Oris) - Emperor Family Academy")
            db.session.add(station)
        if not db.session.query(exists().where(and_(Routes.start_station == 60003478, Routes.end_station == 60003760))).scalar():
            route = Routes(start_station=60003478, end_station=60003760, cost=330, status=0)
            db.session.add(route)
        db.session.commit()


if __name__ == "__main__":
    initial_db()
    exit(0)

# vim: set ts=4 sw=4 et :