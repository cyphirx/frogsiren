import datetime
from time import strptime

from sqlalchemy import and_, or_
from frogsiren import app
import urllib2
import xml.etree.ElementTree as ET
import os
import humanize
from models import db, Stations, Contract, initial_db
from flask import render_template, Markup
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

    datestamp = datetime.datetime.now()

    #if cached_time and datestamp < cached_time:
    #    print "Cache too old"
    #    return


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

        #cached_time = datetime.datetime.strptime(cache_value,"%Y-%m-%d %H:%M%S")



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
            print "Inserting new record!"
            contract = Contract(contractID=contractID, issuerID=issuerID, issuerCorpID=issuerCorpID,
                                assigneeID=assigneeID, acceptorID=acceptorID, startStationID=startStationID,
                                endStationID=endStationID, type=type, status=status, title=title, forCorp=forCorp,
                                availability=availability, dateIssued=dateIssued, dateExpired=dateExpired,
                                dateAccepted=dateAccepted, numDays=numDays, dateCompleted=dateCompleted, price=price,
                                reward=reward, collateral=collateral, buyout=buyout, volume=volume, cached=cached)
            #TODO Add trigger here for contractbot
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
    active_volume = 0
    active_collateral = 0
    active_reward = 0
    content = ""

    retrieve_contracts()

    # Pre-populate station array to cut down on db requests
    stations = Stations.query.all()

    contracts = Contract.query.filter(Contract.type != "ItemExchange").order_by('dateIssued DESC').all()

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
        # Oh god why are we fetching these in the for loop
        # We'll replace one piece of bad code with another!
        source_stationName = "UNKNOWN STATION"
        end_stationName = "UNKNOWN STATION"
        source_systemID = 9999999999
        for station in stations:
            if station.stationID == contract.startStationID:
                source_stationName = station.stationName
                source_systemID = station.systemID
            if station.stationID == contract.endStationID:
                end_stationName = station.stationName

        #TODO Add check on if price is set, volume is higher then max, isk/m3 lower then min, high collateral, not in correct station
        content += '<tr class="' + contract.status + '">\n'
        #TODO FUUUUUUUU, needs to be fixed
        if source_stationName != "UNKNOWN STATION":
            content += '    <td><a href="#" onclick="CCPEVE.showContract(' + str(
                source_systemID) + ',' + str(contract.contractID) + '); return false;">' + str(contract.contractID) + '</a></td>\n'
            content += '    <td>' + source_stationName.split(' ')[0] + '</td>\n'
        else:
            content += '    <td>' + str(contract.contractID) + '</a></td>\n'
            content += '    <td>UNKNOWN ID ( ' + str(contract.startStationID) + ' )</td>\n'

        if end_stationName != "UNKNOWN STATION":
            content += '    <td>' + end_stationName.split(' ')[0] + '</td>\n'
        else:
            content += '    <td>UNKNOWN ID ( ' + str(contract.endStationID) + ' )</td>\n'

        content += '    <td>' + contract.title + '</td>\n'
        content += '    <td>' + contract.dateIssued + '</td>\n'
        content += '    <td>' + contract.dateCompleted + '</td>\n'
        content += '    <td>' + contract.status + '</td>\n'
        content += '    <td>' + str(contract.reward) + '</td>\n'
        content += '    <td>' + str(contract.collateral) + '</td>\n'
        content += '    <td>' + str(contract.volume) + '</td>\n'
        content += '    <td>' + str(isk) + '</td>\n'
        content += '</tr>'

    content += '<tfoot><td colspan=7>Total</td><td>' + humanize.intcomma(
        total_reward) + '</td><td>' + humanize.intcomma(total_collateral) + '</td><td>' + humanize.intcomma(
        total_volume) + '</td><td>&nbsp;</td></thead>'
    content += '<tfoot><td colspan=7>Unaccepted/In Progress</td><td>' + humanize.intcomma(
        active_reward) + '</td><td>' + humanize.intcomma(active_collateral) + '</td><td>' + humanize.intcomma(
        active_volume) + '</td><td>&nbsp;</td></thead>'

    return content


@app.route('/')
def hello_world():
    template = read_contracts()

    return render_template('contracts.html', data=Markup(template), time=cached_time)

# vim: set ts=4 sw=4 et :
