import datetime
from time import strptime

from sqlalchemy import and_, or_
from frogsiren import app
import urllib2
import xml.etree.ElementTree as ET
import os
import humanize
from frogsiren.forms import SigninForm, RoutesForm, StationForm

from models import db, Stations, Contract, initial_db, Routes, Queue
from flask import render_template, Markup, session, redirect, url_for, request, jsonify, abort

from ConfigParser import ConfigParser


def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


Config = ConfigParser()
Config.read("settings.ini")
cached_time = ""

initial_db()

if os.path.isfile('settings.ini'):
    keyID = ConfigSectionMap("api")['keyid']
    vCode = ConfigSectionMap("api")['vcode']

    apiURL = ConfigSectionMap("general")['apiurl']
    debug = ConfigSectionMap("general")['debug']
    interface = ConfigSectionMap("general")['interface']
    port = int(os.environ.get("PORT", 5000))

    # stopgap until we can get connected to Auth
    user = ConfigSectionMap("users")['user']
    password = ConfigSectionMap("users")['password']

else:
    keyID = os.environ['eve_api_keyid']
    vCode = os.environ['eve_api_vcode']

    apiURL = os.environ['eve_api_url']
    debug = os.environ['app_debug']
    interface = os.environ['app_binding_address']
    port = int(os.environ.get("PORT", 5000))

    # stopgap until we can get connected to Auth
    user = os.environ['app_admin_user']
    password = os.environ['app_admin_password']


def retrieve_contracts():
    global cached_time

    print "Retrieving contracts"
    url = apiURL + "/corp/Contracts.xml.aspx?keyID=" + keyID + "&vCode=" + vCode
    request_api = urllib2.Request(url, headers={"Accept": "application/xml"})
    try:
        f = urllib2.urlopen(request_api)
    except:
        print url
        return "Error retrieving character ids url"
    contract_tree = ET.parse(f)
    contract_root = contract_tree.getroot()

    for time in contract_root.findall('.'):
        cache_value = time.find('cachedUntil').text
        cached_time = cache_value
        current_time = time.find('currentTime').text

    for child in contract_root.findall('./result/rowset/*'):
        contractID = child.get("contractID")
        issuerID = child.get("issuerID")
        issuerCorpID = child.get("issuerCorpID")
        assigneeID = child.get("assigneeID")
        acceptorID = child.get("acceptorID")
        startStationID = child.get("startStationID")
        endStationID = child.get("endStationID")
        type = child.get("type")
        status = child.get("status")
        title = child.get("title")
        forCorp = child.get("forCorp")
        availability = child.get("availability")
        dateIssued = child.get("dateIssued")
        dateExpired = child.get("dateExpired")
        dateAccepted = child.get("dateAccepted")
        numDays = child.get("numDays")
        dateCompleted = child.get("dateCompleted")
        price = child.get("price")
        reward = child.get("reward")
        collateral = child.get("collateral")
        buyout = child.get("buyout")
        volume = child.get("volume")
        cached = current_time

        # Let's check if the record exists in the db
        if not Contract.query.filter_by(contractID=contractID).scalar():
            print "Inserting new record! " + type.title() + "Contract " + str(contractID)
            contract = Contract(contractID=contractID, issuerID=issuerID, issuerCorpID=issuerCorpID,
                                assigneeID=assigneeID, acceptorID=acceptorID, startStationID=startStationID,
                                endStationID=endStationID, type=type, status=status, title=title, forCorp=forCorp,
                                availability=availability, dateIssued=dateIssued, dateExpired=dateExpired,
                                dateAccepted=dateAccepted, numDays=numDays, dateCompleted=dateCompleted, price=price,
                                reward=reward, collateral=collateral, buyout=buyout, volume=volume, cached=cached)
            #TODO Add trigger here for contractbot
            if type == "Courier":
                station = Stations.query.filter_by(stationID=startStationID).first()
                if station:
                    stationName = station.stationName
                else:
                    stationName = "UNKNOWN"
                message = "WOOP WOOP! New contract! From: " + stationName.split(' ')[0] + " Reward: " + humanize.intcomma(reward) + "isk Collateral: " + humanize.intcomma(collateral) + " Volume:" + humanize.intcomma(volume) + "m3 Note: " + title
                queue = Queue(note=message,tStamp=datetime.datetime.now())
                db.session.add(queue)
            db.session.add(contract)
        else:
            #Oh dear, something should go here
            contract = Contract.query.filter_by(contractID=contractID).first()
            if contract.status != status:
                print "Updating record!"
                contract.assigneeID = assigneeID
                contract.acceptorID = acceptorID
                contract.status = status
                contract.dateAccepted = dateAccepted
                contract.dateCompleted = dateCompleted
                contract.cached = cached_time
            else:
                continue
    db.session.commit()


def read_contracts():
    total_volume = 0
    total_collateral = 0
    total_reward = 0
    count_progress = 0
    count_pending = 0
    active_volume = 0
    active_collateral = 0
    active_reward = 0
    content = ""

    contracts = db.engine.execute("SELECT c.contractID, s.stationName AS startStation, s.systemID AS startSystemID, c.startStationID, e.stationName AS endStation, c.endStationId, c.status, c.title, c.dateIssued, c.dateCompleted, c.reward, c.collateral, c.volume, r.cost AS fee FROM contract AS c LEFT JOIN stations AS s on c.startStationID = s.stationID LEFT JOIN stations AS e ON c.endStationId = e.stationID LEFT JOIN  routes AS r ON (c.startStationID = r.start_station AND c.endStationID = r.end_station) WHERE c.type = 'Courier' ORDER BY dateIssued DESC ").fetchall()

    for contract in contracts:

        # Start working towards display
        total_volume += contract.volume
        total_collateral += contract.collateral
        total_reward += contract.reward
        isk = round(contract.reward / contract.volume, 2)
        if type == "ItemExchange":
            continue
        if contract.status == "InProgress" or contract.status == "Outstanding":
            active_collateral += contract.collateral
            active_reward += contract.reward
            active_volume += contract.volume

        if contract.status == "InProgress":
            count_progress += 1

        if contract.status == "Outstanding":
            count_pending += 1


        #TODO Add check on if price is set, volume is higher then max, isk/m3 lower then min, high collateral, not in correct station
        content += '<tr class="' + contract.status + '">\n'

        if contract.startStation:
            javascript = '    <td><a href="#" onclick="CCPEVE.showContract(' + str(
                contract.startSystemID) + ',' + str(contract.contractID) + ')">' + str(
                contract.contractID) + '</a></td>\n'
            content += javascript
            content += '    <td>' + contract.startStation.split(' ')[0] + '</td>\n'
        else:
            content += '    <td>' + str(contract.contractID) + '</a></td>\n'
            content += '    <td>UNKNOWN ID ( ' + str(contract.startStationID) + ' )</td>\n'

        if contract.endStation:
            content += '    <td>' + contract.endStation.split(' ')[0] + '</td>\n'
        else:
            content += '    <td>UNKNOWN ID ( ' + str(contract.endStationID) + ' )</td>\n'




        content += '    <td>' + contract.title + '</td>\n'
        content += '    <td>' + contract.dateIssued + '</td>\n'
        content += '    <td>' + contract.dateCompleted + '</td>\n'
        content += '    <td>' + contract.status + '</td>\n'
        content += '    <td>' + str(contract.reward) + '</td>\n'
        content += '    <td>' + str(contract.collateral) + '</td>\n'
        content += '    <td>' + str(contract.volume) + '</td>\n'
        if contract.fee > isk:
            color = "red"
        else:
            color = "green"

        content += '    <td style="background-color:' + color + '">' + str(isk) + '</td>\n'
        content += '</tr>'

    content += '<tfoot><td>Outstanding</td><td style="text-align: center"><b>' + str(count_pending) + '</b></td><td colspan=5 style="text-align: right">Total</td><td>' + humanize.intcomma(
        total_reward) + '</td><td>' + humanize.intcomma(total_collateral) + '</td><td>' + humanize.intcomma(
        total_volume) + '</td><td>&nbsp;</td></tfoot>\n'
    content += '<tfoot><td>Inprogress</td><td style="text-align: center"><b>' + str(count_progress) + '</b></td><td colspan=5 style="text-align: right">Unaccepted/In Progress</td><td>' + humanize.intcomma(
        active_reward) + '</td><td>' + humanize.intcomma(active_collateral) + '</td><td>' + humanize.intcomma(
        active_volume) + '</td><td>&nbsp;</td></tfoot>\n'

    return content


@app.route('/api/pending')
def api_inprogress():
        contracts = db.engine.execute("SELECT c.contractID, s.stationName AS startStation, s.systemID AS startSystemID, c.startStationID, e.stationName AS endStation, c.endStationId, c.status, c.title, c.dateIssued, c.dateCompleted, c.reward, c.collateral, c.volume, r.cost AS fee FROM contract AS c LEFT JOIN stations AS s on c.startStationID = s.stationID LEFT JOIN stations AS e ON c.endStationId = e.stationID LEFT JOIN  routes AS r ON (c.startStationID = r.start_station AND c.endStationID = r.end_station) WHERE c.type = 'Courier' AND (c.status = 'InProgess' OR c.status = 'Pending')  ORDER BY dateIssued DESC ").fetchall()

@app.route('/api/queue', methods=['GET','POST'])
def display_queue():
    note = []


    if request.method == 'POST':
        # Time to do some deleting
        statement = "DELETE FROM queue"
        db.engine.execute(statement)

    # Let's build the statement
    statement = "SELECT note, tStamp FROM queue"
    tables = db.engine.execute(statement)


    for result in tables:

        note += [ { "note": result.note,
                   "tstamp": result.tStamp
                          }]
    if len(note) == 0:
        abort(404)
    return jsonify( { 'messages': note } )




@app.route('/report')
def display_report():
    #SELECT COUNT(*), SUM(reward), SUM(reward) / COUNT(*) AS avg_reward, DATE(dateCompleted) FROM contract WHERE type = 'Courier' AND status = 'Completed' GROUP BY DATE(dateCompleted)
    #SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS avg_time, MAX((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60 )  FROM contract WHERE type = 'Courier' AND status = 'Completed'
    return render_template('reports.html')

@app.route('/contracts')
def hello_world():
    if not 'email' in session:
        return redirect(url_for('default_display'))

    template = read_contracts()
    return render_template('contracts.html', data=Markup(template), time=cached_time)


@app.route('/')
def default_display():
    route_info = ""
    running_average = ""
    overall_average = ""

    routes = db.engine.execute("SELECT s.stationName as start, e.stationName as end, r.cost as cost FROM routes AS r JOIN stations AS s on s.stationID=r.start_station JOIN stations AS e on e.stationID = r.end_station WHERE status = 1")
    for route in routes:
        route_info += "<tr><td>" + route.start + "</td><td><=></td><td>" + route.end + "</td><td>=</td><td>" + str(route.cost) + "</td></tr>\n"

    running_sql = db.engine.execute("SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS return_value FROM contract WHERE type = 'Courier' AND dateCompleted BETWEEN DATETIME('now', '-5 days') AND DATETIME('now', 'localtime') AND status IS NOT 'Rejected'")
    for result in running_sql:
        running_average = "%.2f" % result.return_value
    overall_sql = db.engine.execute("SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS return_value FROM contract WHERE type = 'Courier' AND status IS NOT 'Rejected'")
    for oresult in overall_sql:
        overall_average = "%.2f" % oresult.return_value

    return render_template('unauthed.html', route_info=Markup(route_info), running_average=running_average, overall_average=overall_average)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SigninForm()

    if 'email' in session:
        return redirect(url_for('hello_world'))

    if request.method == 'POST':
        if form.name.data == user and form.password.data == password:
            session['email'] = form.name.data
            return redirect(url_for('hello_world'))
        else:
            return render_template('signin.html', form=form)

    elif request.method == 'GET':
        return render_template('signin.html', form=form)

#TODO Create /delete/route/<id> method and /disable/route
@app.route('/routes', methods=['GET', 'POST'])
def routes():
    if not 'email' in session:
        return redirect(url_for('hello_world'))
    station_content = ""
    route_content = ""

    rform = RoutesForm()
    sform = StationForm()

    #TODO FIX MESSAGING HERE!
    if request.method == 'POST':
        if request.form['submit'] == 'Add A Station':
            #Adding a station, station things go here
            station = Stations(stationID=sform.station_id.data,stationName=sform.station_name.data,systemID=sform.system_id.data)
            db.session.add(station)
            db.session.commit()
            print "Adding a station id " + sform.station_id.data
        elif request.form['submit'] == 'Add Route':
            route = Routes(start_station=rform.start_station_id.data,end_station=rform.end_station_id.data,cost=rform.cost.data,status=1)
            db.session.add(route)
            db.session.commit()
            print "Adding a route"

    # Filling out route information
    routes = db.engine.execute("SELECT r.route_id as id, s.stationName as start, e.stationName as end, r.cost as cost, r.status as status FROM routes AS r JOIN stations AS s on s.stationID=r.start_station JOIN stations AS e on e.stationID = r.end_station WHERE status = 1")
    #routes = Routes.query.all()
    for route in routes:
        if route.status == True:
            status_line = "Enabled"
        else:
            status_line = "Disabled"
        route_content += "<tr><td>" + str(route.start) + "</td><td>" + str(route.end) + "</td><td>" + str(route.cost) + "</td><td>" + status_line + "</td><td><a href='/enable/route/" + str(route.id) + "'><img src='/static/img/enable.png' alt=\"Enable\"></a> <a href='/disable/route/" + str(route.id) + "'><img src='/static/img/disable.png' alt=\"Disable\"></a> <a href='/delete/route/" + str(route.id) + "'><img src='/static/img/remove.png' alt=\"Remove\"></a></td></tr>\n"

    stations = Stations.query.all()

    for station in stations:
        station_content += "<tr><td> " + station.stationName + "</td><td>" + str(station.stationID) + "</td><td>" + str(station.systemID) + "</td></tr>\n"


    return render_template('routes.html', rform=rform, sform=sform, route_content=Markup(route_content), station_content=Markup(station_content))


@app.route('/check')
def check_contracts():
    retrieve_contracts()
    return "Retrieved"


    # vim: set ts=4 sw=4 et :