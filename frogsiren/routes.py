import datetime
import json
import urllib2
import xml.etree.ElementTree as ET
import os
from ConfigParser import ConfigParser

import humanize
from flask import render_template, Markup, session, redirect, url_for, request, jsonify, abort


from frogsiren import app
from frogsiren.forms import SigninForm, RoutesForm, StationForm, NoteForm
from models import db, Stations, Contract, initial_db, Routes, Queue, Player, PlayerNotes


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

# Minimum required for reward, should be settable variable in-app
rewardMin = 10000000

initial_db()

if os.path.isfile('settings.ini'):
    keyID = ConfigSectionMap("api")['keyid']
    vCode = ConfigSectionMap("api")['vcode']

    apiURL = ConfigSectionMap("general")['apiurl']
    debug = ConfigSectionMap("general")['debug']
    interface = ConfigSectionMap("general")['interface']
    localAPI = ConfigSectionMap("general")['localapi']
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
    ids = "93746362"
    i = 0

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
            if type == "Courier":
                # Look up issuer internally and hit API if unknown
                player = Player.query.filter_by(characterID=issuerID).all()
                if len(player) < 1:
                    i += 1

                station = Stations.query.filter_by(stationID=startStationID).first()
                if station:
                    stationName = station.stationName
                else:
                    stationName = "UNKNOWN"
                message = "WOOP WOOP! New contract! From: " + stationName.split(' ')[
                    0] + " Reward: " + humanize.intcomma(reward) + "isk Collateral: " + humanize.intcomma(
                    collateral) + " Volume:" + humanize.intcomma(volume) + "m3 Note: " + title
                queue = Queue(note=message, tStamp=datetime.datetime.now())
                db.session.add(queue)
            db.session.add(contract)
        else:
            # Oh dear, something should go here
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

    check_stations(False)
    if i > 0:
        check_players()

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
    reward_title = ""
    collat_title = ""

    contracts = db.engine.execute(
        "SELECT c.contractID, p.characterName AS issuer, c.issuerID, s.stationName AS startStation, s.systemID AS startSystemID, c.startStationID, e.stationName AS endStation, c.endStationId, c.status, c.title, c.dateIssued, c.dateCompleted, c.reward, c.collateral, c.volume, r.cost AS fee FROM contract AS c LEFT JOIN stations AS s on c.startStationID = s.stationID LEFT JOIN stations AS e ON c.endStationId = e.stationID LEFT JOIN  routes AS r ON ((c.startStationID = r.start_station OR c.endStationId = r.start_station) AND (c.endStationID = r.end_station OR c.startStationID = r.end_station ) ) LEFT JOIN player AS p ON c.issuerID = p.characterID WHERE c.type = 'Courier' ORDER BY dateIssued DESC LIMIT 45").fetchall()

    for contract in contracts:

        # Start working towards display
        isk = round(contract.reward / contract.volume, 2)
        if type == "ItemExchange":
            continue
        if contract.status == "InProgress" or contract.status == "Outstanding":
            active_collateral += contract.collateral
            active_reward += contract.reward
            active_volume += contract.volume

        if contract.status == "InProgress":
            count_progress += 1
            total_reward += contract.reward
            total_collateral += contract.collateral
            total_volume += contract.volume

        if contract.status == "Outstanding":
            count_pending += 1
            total_reward += contract.reward
            total_collateral += contract.collateral
            total_volume += contract.volume

        # Colorize weird route
        # Colorize volume
        if contract.volume > 320000:
            vol_color = "red"
        else:
            vol_color = "none"
        reward_title = ""

        # Colorize incorrect reward
        if contract.fee > isk:
            reward_color = "red"
        elif isk >= contract.fee > 0:
            reward_color = "none"
        else:
            reward_color = "yellow"
            reward_title = "Unknown route"

        if contract.fee >= rewardMin:
            reward_color = "red"
            reward_title = "Low Reward"

        # Colorize incorrect collat
        collat_color = "none"
        collat_title = ""
        if contract.collateral > 0:
            if contract.fee:
                calcReward = contract.fee * contract.volume + contract.collateral * .05
                if calcReward >= contract.reward:
                    collat_color = "red"
                    collat_title = "Reward should be: " + humanize.intcomma(calcReward)
            else:
                collat_color = "yellow"

        # Start building a row
        content += '<tr class="' + contract.status + '">\n'

        if contract.startStation:
            javascript = '    <td><a href="#" onclick="CCPEVE.showContract(' + str(
                contract.startSystemID) + ',' + str(contract.contractID) + ')">' + str(
                contract.contractID) + '</a></td>\n'
            content += javascript
            content += '    <td>' + contract.startStation.split(' ')[0] + '</td>\n'
        else:
            content += '    <td>' + str(contract.contractID) + '</a></td>\n'
            content += '    <td color="red">UNKNOWN ID ( ' + str(contract.startStationID) + ' )</td>\n'

        if contract.endStation:
            content += '    <td>' + contract.endStation.split(' ')[0] + '</td>\n'
        else:
            content += '    <td color="red">UNKNOWN ID ( ' + str(contract.endStationID) + ' )</td>\n'

        content += '    <td>' + contract.title + '</td>\n'
        content += '    <td>' + contract.dateIssued + '</td>\n'
        if contract.issuer:
            query = 'SELECT p.characterName, SUM(c.reward) AS reward, SUM(c.collateral) AS collat, SUM(c.volume) AS volume, COUNT(*) AS total FROM contract AS c LEFT JOIN player AS p ON c.issuerID == p.characterID WHERE c.type == "Courier" AND p.characterName LIKE "' + contract.issuer + '%" GROUP BY c.issuerID LIMIT 1'
            players = db.engine.execute(query)

            for player in players:
                title = "For player: " + player.characterName + "&#013;"
                title += "Total Rewards: " + humanize.intcomma(player.reward) + "&#013;"
                title += "Total Collat: " + humanize.intcomma(player.collat) + "&#013;"
                title += "Total Volume: " + humanize.intcomma(player.volume) + "&#013;"
                title += "Courier Contracts: " + str(player.total)
            note = db.session.query(PlayerNotes).filter(PlayerNotes.characterID==contract.issuerID).first()
            if note:
                noteVal = "*"
            else:
                noteVal = ""
            content += '    <td title="' + title + '"><a href="player/'+ str(contract.issuerID) +'">' + contract.issuer + noteVal + '</a></td>\n'
        else:
            content += '    <td>Issuer unknown!</td>\n'
        content += '    <td>' + contract.status + '</td>\n'
        content += '    <td style="background-color:' + reward_color + '" title="' + reward_title + '">' + humanize.intcomma(
            contract.reward) + '</td>\n'
        content += '    <td style="background-color:' + collat_color + '" title="' + collat_title + '">' + humanize.intcomma(
            contract.collateral) + '</td>\n'
        content += '    <td style="background-color:' + vol_color + '">' + humanize.intcomma(
            contract.volume) + '</td>\n'

        content += '    <td style="background-color:' + reward_color + '">' + str(isk) + '</td>\n'
        content += '</tr>'

    # Build SQL queries to count item totals, total value hauled, total isk hauled
    # SELECT COUNT(*), status FROM contract WHERE type = 'Courier' GROUP BY status
    # SELECT SUM(reward), SUM(volume) FROM contract WHERE type = 'Courier' AND status = 'Completed'

    content += '<tfoot><td colspan=7 style="text-align: right">Total</td><td>' + humanize.intcomma(
        total_reward) + '</td><td>' + humanize.intcomma(total_collateral) + '</td><td>' + humanize.intcomma(
        total_volume) + '</td><td>&nbsp;</td></tfoot>\n'

    return content


@app.route('/api/pending')
def api_inprogress():
    contracts = db.engine.execute(
        "SELECT c.contractID, s.stationName AS startStation, s.systemID AS startSystemID, c.startStationID, e.stationName AS endStation, c.endStationId, c.status, c.title, c.dateIssued, c.dateCompleted, c.reward, c.collateral, c.volume, r.cost AS fee FROM contract AS c LEFT JOIN stations AS s on c.startStationID = s.stationID LEFT JOIN stations AS e ON c.endStationId = e.stationID LEFT JOIN  routes AS r ON (c.startStationID = r.start_station AND c.endStationID = r.end_station) WHERE c.type = 'Courier' AND (c.status = 'InProgess' OR c.status = 'Pending')  ORDER BY dateIssued DESC ").fetchall()


@app.route('/api/queue', methods=['GET', 'POST'])
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
        note += [{"note": result.note,
                  "tstamp": result.tStamp
                 }]
    if len(note) == 0:
        abort(404)
    return jsonify({'messages': note})


@app.route('/report')
def display_report():
    # SELECT COUNT(*), SUM(reward), SUM(reward) / COUNT(*) AS avg_reward, DATE(dateCompleted) FROM contract WHERE type = 'Courier' AND status = 'Completed' GROUP BY DATE(dateCompleted)
    #SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS avg_time, MAX((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60 )  FROM contract WHERE type = 'Courier' AND status = 'Completed'
    return render_template('reports.html')


@app.route('/stations')
def check_stations(cleanStations = True):
    # Stub for nightly cleanup of stations list
    if cleanStations == True:
        print "Truncating table"
    endStations = db.session.query(Contract).outerjoin(Stations, Contract.endStationID == Stations.stationID).filter(
        Stations.stationName == None).filter(Contract.type == 'Courier').order_by(Contract.endStationID).group_by(Contract.endStationID).all()

    for endStation in endStations:
        url = localAPI + "/stationID/" + str(endStation.endStationID)
        try:
            j = urllib2.urlopen(url)
        except urllib2.URLError, e:
            if e.code == 404:
                print "No stations found!"
            else:
                message = "Unknown error!"
        else:
            j_obj = json.load(j)

            system = j_obj['solarSystem']
            for item in system:
                print item['stationID'], item['stationName'],item['solarSystemID']
                station = Stations(stationID=int(item['stationID']), stationName=item['stationName'], systemID=int(item['solarSystemID']))
                print "Adding " + item['stationName']
                db.session.add(station)

    db.session.commit()
    startStations = db.session.query(Contract).outerjoin(Stations, Contract.startStationID == Stations.stationID).filter(
        Stations.stationName == None).filter(Contract.type == 'Courier').order_by(Contract.startStationID).group_by(Contract.startStationID).all()

    for startStation in startStations:
        url = localAPI + "/stationID/" + str(startStation.startStationID)
        try:
            j = urllib2.urlopen(url)
        except urllib2.URLError, e:
            if e.code == 404:
                print "No stations found!"
            else:
                message = "Unknown error!"
        else:
            j_obj = json.load(j)

            system = j_obj['solarSystem']
            for item in system:
                station = Stations(stationID=int(item['stationID']), stationName=item['stationName'], systemID=int(item['solarSystemID']))
                print "Adding " + item['stationName']
                db.session.add(station)


    db.session.commit()
    return "Hi"


@app.route('/players')
def check_players():
    players = db.session.query(Contract).outerjoin(Player, Contract.issuerID == Player.characterID).filter(
        Player.characterName == None).order_by(Contract.issuerID).group_by(Contract.issuerID).all()
    i = 0
    ids = "93746362"
    for player in players:
        i += 1
        if i >= 200:
            print "Hit player cap"
            break
        ids += "," + str(player.issuerID)
    if i > 0:
        url = apiURL + "/eve/CharacterAffiliation.xml.aspx?ids=" + ids
        request_api = urllib2.Request(url, headers={"Accept": "application/xml"})
        try:
            f = urllib2.urlopen(request_api)
        except:
            print url
            return "Error retrieving character ids url"
        player_tree = ET.parse(f)
        player_root = player_tree.getroot()
        for time in player_root.findall('.'):
            current_time = time.find('currentTime').text

        for child in player_root.findall('./result/rowset/*'):
            characterID = child.get("characterID")
            if characterID == "93746362":
                continue
            characterName = child.get("characterName")
            corporationID = child.get("corporationID")
            corporationName = child.get("corporationName")
            allianceID = child.get("allianceID")
            allianceName = child.get("allianceName")
            if not allianceName:
                allianceName = ""
                allianceID = 0
            print characterName
            player = Player(characterName=characterName,characterID=characterID,corporationName=corporationName,corporationID=corporationID,allianceName=allianceName,allianceID=allianceID,dateAdded=current_time,dateUpdated=current_time)
            db.session.add(player)

    db.session.commit()
    return "Oh my!"

@app.route('/player/<int:id>', methods=['GET','POST'])
def display_player(id):
    if 'email' not in session:
        return redirect(url_for('default_display'))
    player = db.session.query(Player).filter( Player.characterID == id).first()
    if player:
        noteForm = NoteForm()
        if request.method == "POST":
            note = PlayerNotes(characterID=player.characterID,note=noteForm.note.data,addedBy=session['email'],dateAdded=cached_time,status=1)
            db.session.add(note)
            db.session.commit()
        # Build up notes list
        notes = db.session.query(PlayerNotes).filter(PlayerNotes.characterID==id).all()
        # Build summary
        sql = "SELECT characterName, SUM(reward) AS reward, SUM(collateral) AS collateral, SUM(volume) AS volume, COUNT(*) AS count FROM contract LEFT JOIN player ON contract.issuerID = player.characterID WHERE issuerID = " + str(id) + " GROUP BY issuerID"
        summary = db.session.execute(sql).first()

        # Build contract table
        sql = "SELECT ss.stationName as startStation, es.stationName as endStation, reward, collateral, volume, dateIssued, dateCompleted, status FROM contract LEFT JOIN stations ss ON contract.startStationID = ss.stationID LEFT JOIN stations es ON contract.endStationID = es.stationID WHERE issuerID = " + str(id) + " ORDER BY dateIssued"
        contracts = db.engine.execute(sql).fetchall()

        statement = ""
        for contract in contracts:
            statement += "<tr>\n"
            statement += "  <td>" + contract.startStation.split(' ')[0] + "</td>\n"
            statement += "  <td>" + contract.endStation.split(' ')[0] + "</td>\n"
            statement += "  <td>" + humanize.intcomma(contract.reward) + "</td>\n"
            statement += "  <td>" + humanize.intcomma(contract.collateral) + "</td>\n"
            statement += "  <td>" + humanize.intcomma(contract.volume) + "</td>\n"
            statement += "  <td>" + contract.dateIssued + "</td>\n"
            statement += "  <td>" + contract.dateCompleted + "</td>\n"
            statement += "  <td>" + contract.status + "</td>\n"
            statement += "</tr>\n"

        return render_template('player.html', player_data=player, notes=notes, noteForm=noteForm, contracts=Markup(statement), summary=summary)
    else:
        return render_template('player.html')

@app.route('/contracts')
def hello_world():
    if not 'email' in session:
        return redirect(url_for('default_display'))

    sql = "SELECT COUNT(*) AS total, status FROM contract WHERE type = 'Courier' GROUP BY status ORDER BY status"
    statuses = db.engine.execute(sql).fetchall()
    content = 'Contract Totals<br />\n<table>\n<tr>'
    for status in statuses:
        content += '<td width="75">' + status.status + '</td><td width="25" style="text-align: center"><b>' + str(
            status.total) + '</b></td>\n'
    sql = "SELECT SUM(reward) AS reward, SUM(collateral) AS collat, SUM(volume) AS volume FROM contract WHERE type = 'Courier' AND status = 'Completed'"
    totals = db.engine.execute(sql).first()

    content += ""
    content += '</tr>\n</table>\n'

    template = read_contracts()
    return render_template('contracts.html', data=Markup(template), summary=Markup(content), time=cached_time)


@app.route('/')
def default_display():
    route_info = ""
    running_average = ""
    overall_average = ""

    routes = db.engine.execute(
        "SELECT s.stationName as start, e.stationName as end, r.cost as cost FROM routes AS r JOIN stations AS s on s.stationID=r.start_station JOIN stations AS e on e.stationID = r.end_station WHERE status = 1")
    for route in routes:
        route_info += "<tr><td>" + route.start + "</td><td><=></td><td>" + route.end + "</td><td>=</td><td>" + str(
            route.cost) + "</td></tr>\n"

    running_sql = db.engine.execute(
        "SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS return_value FROM contract WHERE type = 'Courier' AND dateCompleted BETWEEN DATETIME('now', '-5 days') AND DATETIME('now', 'localtime') AND status IS NOT 'Rejected'")
    if running_sql:
        for result in running_sql:
            running_average = "%.2f" % result.return_value
    overall_sql = db.engine.execute(
        "SELECT AVG((strftime('%s', dateCompleted) - strftime('%s',dateIssued)) / 60 / 60) AS return_value FROM contract WHERE type = 'Courier' AND status IS NOT 'Rejected'")
    for oresult in overall_sql:
        overall_average = "%.2f" % oresult.return_value

    return render_template('unauthed.html', route_info=Markup(route_info), running_average=running_average,
                           overall_average=overall_average)


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


# TODO Create /delete/route/<id> method and /disable/route
@app.route('/delete/route/<id>', methods=['GET', 'POST'])
def del_route(id):
    statement = "DELETE FROM routes WHERE route_id = " + id
    db.engine.execute(statement)
    return "Deleted"


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
            station = Stations(stationID=sform.station_id.data, stationName=sform.station_name.data,
                               systemID=sform.system_id.data)
            db.session.add(station)
            db.session.commit()
            print "Adding a station id " + sform.station_id.data
        elif request.form['submit'] == 'Add Route':
            route = Routes(start_station=rform.start_station_id.data, end_station=rform.end_station_id.data,
                           cost=rform.cost.data, status=1)
            db.session.add(route)
            db.session.commit()
            print "Adding a route"

    # Filling out route information
    routes = db.engine.execute(
        "SELECT r.route_id as id, s.stationName as start, e.stationName as end, r.cost as cost, r.status as status FROM routes AS r JOIN stations AS s on s.stationID=r.start_station JOIN stations AS e on e.stationID = r.end_station WHERE status = 1 ORDER BY s.stationName, e.stationName")
    #routes = Routes.query.all()
    for route in routes:
        if route.status == True:
            status_line = "Enabled"
        else:
            status_line = "Disabled"
        route_content += "<tr><td>" + str(route.start) + "</td><td>" + str(route.end) + "</td><td>" + str(
            route.cost) + "</td><td>" + status_line + "</td><td><a href='/enable/route/" + str(
            route.id) + "'><img src='/static/img/enable.png' alt=\"Enable\"></a> <a href='/disable/route/" + str(
            route.id) + "'><img src='/static/img/disable.png' alt=\"Disable\"></a> <a href='/delete/route/" + str(
            route.id) + "'><img src='/static/img/remove.png' alt=\"Remove\"></a></td></tr>\n"

    stations = Stations.query.all()

    for station in stations:
        station_content += "<tr><td> " + station.stationName + "</td><td>" + str(station.stationID) + "</td><td>" + str(
            station.systemID) + "</td></tr>\n"

    return render_template('routes.html', rform=rform, sform=sform, route_content=Markup(route_content),
                           station_content=Markup(station_content))


@app.route('/check')
def check_contracts():
    retrieve_contracts()
    return "Retrieved"


    # vim: set ts=4 sw=4 et :