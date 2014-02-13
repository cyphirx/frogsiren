from frogsiren import app
import urllib2
import xml.etree.ElementTree as ET
import os
import humanize
from models import db, Stations, Contract

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


def read_contracts():
    global cached_time
    total_volume = 0
    total_collateral = 0
    total_reward = 0
    active_volume = 0
    active_collateral = 0
    active_reward = 0
    url = apiURL + "/corp/Contracts.xml.aspx?keyID=" + keyID + "&vCode=" + vCode
    request_api = urllib2.Request(url, headers={"Accept": "application/xml"})
    try:
        f = urllib2.urlopen(request_api)
    except:
        print url
        return "Error retrieving character ids url"

    contract_tree = ET.parse(f)
    contract_root = contract_tree.getroot()
    content = ""
    for time in contract_root.findall('.'):
        cached_time = time.find('cachedUntil').text
    for child in contract_root.findall('./result/rowset/*'):
        contractID = child.get("contractID")
        source_station_id = child.get("startStationID")



        end_station_id = child.get("endStationID")
        type = child.get("type")
        status = child.get("status")
        title = child.get("title")
        date_issued = child.get("dateIssued")
        days = child.get("numDays")
        price = float(child.get("price"))
        reward = float(child.get("reward"))
        collateral = float(child.get("collateral"))
        volume = float(child.get("volume"))
        total_volume += volume
        total_collateral += collateral
        total_reward += reward
        isk = round(reward / volume, 2)
        if type == "ItemExchange":
            continue
        if status == "InProgress" or status == "Outstanding":
            active_collateral += collateral
            active_reward += reward
            active_volume += volume
        start_station = Stations.query.filter_by(stationID=source_station_id).first()
        #TODO Add check on if price is set, volume is higher then max, isk/m3 lower then min, high collateral, not in correct station
        end_station = Stations.query.filter_by(stationID=end_station_id).first()
        content += '<tr class="' + status + '">\n'
        content += '    <td><a href="#" onclick="CCPEVE.showContract(' + str(start_station.systemID) + ',' + contractID + ')">' + contractID + '</a></td>\n'
        content += '    <td>' + start_station.stationName.split(' ')[0] + '</td>\n'
        content += '    <td>' + end_station.stationName.split(' ')[0] + '</td>\n'
        content += '    <td>' + type + '</td>\n'
        content += '    <td>' + date_issued + '</td>\n'
        content += '    <td>' + status + '</td>\n'
        content += '    <td>' + str(reward) + '</td>\n'
        content += '    <td>' + str(collateral) + '</td>\n'
        content += '    <td>' + str(volume) + '</td>\n'
        content += '    <td>' + str(isk) + '</td>\n'
        content += '</tr>'

    content += '<tfoot><td colspan=6>Total</td><td>' + humanize.intcomma(total_reward) + '</td><td>' + humanize.intcomma(total_collateral) + '</td><td>' + humanize.intcomma(total_volume) + '</td><td>&nbsp;</td></thead>'
    content += '<tfoot><td colspan=6>Unaccepted/In Progress</td><td>' + humanize.intcomma(active_reward) + '</td><td>' + humanize.intcomma(active_collateral) + '</td><td>' + humanize.intcomma(active_volume) + '</td><td>&nbsp;</td></thead>'

    return content




@app.route('/')
def hello_world():
    template = read_contracts()

    return render_template('contracts.html', data=Markup(template), time=cached_time)
