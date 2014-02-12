from frogsiren import app
import urllib2
import xml.etree.ElementTree as ET
import os
import math
import humanize

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

if os.path.isfile('settings.ini'):
    keyID = ConfigSectionMap("api")['keyid']
    vCode = ConfigSectionMap("api")['vcode']

    apiURL = ConfigSectionMap("general")['apiurl']
    debug =  ConfigSectionMap("general")['debug']
    interface =  ConfigSectionMap("general")['interface']
    port = int(os.environ.get("PORT", 5000))

    # stopgap until we can get connected to Auth
    user =  ConfigSectionMap("users")['user']
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

    for child in contract_root.findall('./result/rowset/*'):
        source_station_id = child.get("startStationID")



        end_station_id = child.get("endStationID")
        type = child.get("type")
        status = child.get("status")
        title = child.get("title")
        date_issued = child.get("dateIssued")
        days = child.get("numDays")
        price = child.get("price")
        reward = child.get("reward")
        collateral = child.get("collateral")
        volume = float(child.get("volume"))
        content += '<tr class="' + status + '">\n'
        content += '    <td>' + source_station_id + '</td>\n'
        content += '    <td>' + end_station_id + '</td>\n'
        content += '    <td>' + type + '</td>\n'
        content += '    <td>' + date_issued + '</td>\n'
        content += '    <td>' + status + '</td>\n'
        content += '    <td>' + humanize.intcomma(price) + '</td>\n'
        content += '    <td>' + humanize.intcomma(reward) + '</td>\n'
        content += '    <td>' + humanize.intcomma(collateral) + '</td>\n'
        content += '    <td>' + humanize.intcomma(math.ceil(volume)) + '</td>\n'
        content += '</tr>'

    return content




@app.route('/')
def hello_world():
    template = read_contracts()

    return render_template('contracts.html', data=Markup(template))
