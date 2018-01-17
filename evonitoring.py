#!/usr/bin/env python2

from __future__ import print_function
import httplib
import sys
import urllib
import syslog

# you need to install py-requests (OpenBSD) or python-requests (Debian)
# you need to install py-yaml     (OpenBSD) or python-yaml     (Debian)
import requests
import yaml

CONFIG = "/etc/evonitoring.yml"


def pushover(alert):
    conn = httplib.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.urlencode({
                     "token": pushover_token,
                     "user": pushover_user,
                     "message": alert}),
                 {"Content-type": "application/x-www-form-urlencoded"})
    conn.getresponse()


def twilio(oncallnumber, alert):
    payload = {
        'From': twilio_available_number,
        'To': "+" + oncallnumber,
        'Body': alert
    }
    # send the text with twilio's api
    p = requests.post("https://api.twilio.com/2010-04-01/Accounts/" +
                      twilio_account_sid + "/Messages",
                      data=payload,
                      auth=(twilio_account_sid, twilio_auth_token))
    if p.status_code != 201:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending twilio')
    syslog.syslog('SMS sent with twilio to ' + oncallnumber)


def smsmode(oncallnumber, alert):
    payload = {"numero": oncallnumber,
               "message": alert,
               "pseudo": smsmode_user,
               "pass": smsmode_pass}
    g = requests.get("http://" + smsmode_host + "/http/1.6/sendSMS.do",
                     params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending smsmode')
    syslog.syslog('SMS sent with smsmode to ' + oncallnumber)


def mobyt(oncallnumber, alert):
    payload = {"rcpt": "+" + oncallnumber,
               "data": alert,
               "user": mobyt_user,
               "pass": mobyt_pass,
               "sender": mobyt_sender,
               "qty": "n"}
    g = requests.get("http://" + mobyt_host + "/sms/send.php",
                     params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending mobyt')
    syslog.syslog('SMS sent with mobyt to ' + oncallnumber)


def irc(alert):
    # concat the multiple lines on a single line
    uniline = []
    for l in alert:
        if l == '\n':
            l = ' '
        uniline.append(l)
    uniline.append('\n')
    with open(irc_fifo, "a") as f:
        f.write(''.join(uniline))
    syslog.syslog('Alert sent to irc as well')

# which alerting system should we use: mobyt, twilio
def decide_alerting(oncallnumber, alert):
    if pushover_active == "True":
        # it must not block nor kill the script
        try:
            pushover(alert)
        except:
            pass
    # select the right sender depend of the number
    if oncallnumber[0:2] == "33":
        if FR_sender == "mobyt":
            mobyt(oncallnumber, alert)
        elif FR_sender == "smsmode":
            smsmode(oncallnumber, alert)
        elif FR_sender == "twilio":
            twilio(oncallnumber, alert)
    else:
        twilio(oncallnumber, alert)

    if irc_active == "True":
        # it must not block nor kill the script
        try:
            irc(alert)
        except:
            pass


def readconf():
    with open(CONFIG, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    # twilio api key
    global twilio_account_sid
    global twilio_auth_token
    global twilio_available_number
    try:
        twilio_account_sid = cfg["Twilio"]["account_sid"]
        twilio_auth_token = cfg["Twilio"]["auth_token"]
        twilio_available_number = cfg["Twilio"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Twilio config couldn't be parsed")

    # pushover
    global pushover_token
    global pushover_user
    global pushover_active
    try:
        pushover_token = cfg["Pushover"]["token"]
        pushover_user = cfg["Pushover"]["user"]
        pushover_active = cfg["Pushover"]["active"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Pushover config couldn't be parsed")

    # sender system
    global MOBYT_BIN
    global FR_sender
    if cfg["FR-Astreinte-send"] == "mobyt":
        FR_sender = "mobyt"
    elif cfg["FR-Astreinte-send"] == "smsmode":
        FR_sender = "smsmode"
    elif cfg["FR-Astreinte-send"] == "twilio":
        FR_sender = "twilio"
    else:
        syslog.syslog(syslog.LOG_ERR,
                      "Config erroneous FR-Astreinte-send is wrong")

    # mobyt
    global mobyt_ip
    global mobyt_port
    global mobyt_host
    global mobyt_user
    global mobyt_pass
    global mobyt_sender
    try:
        mobyt_ip = cfg["Mobyt"]["ip"]
        mobyt_port = cfg["Mobyt"]["port"]
        mobyt_host = cfg["Mobyt"]["host"]
        mobyt_user = cfg["Mobyt"]["user"]
        mobyt_pass = cfg["Mobyt"]["pass"]
        mobyt_sender = cfg["Mobyt"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Mobyt config couldn't be parsed")

    # smsmode
    global smsmode_ip
    global smsmode_port
    global smsmode_host
    global smsmode_user
    global smsmode_pass
    try:
        smsmode_ip = cfg["Smsmode"]["ip"]
        smsmode_port = cfg["Smsmode"]["port"]
        smsmode_host = cfg["Smsmode"]["host"]
        smsmode_user = cfg["Smsmode"]["user"]
        smsmode_pass = cfg["Smsmode"]["pass"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Smsmode config couldn't be parsed")

    # IRC
    global irc_active
    global irc_fifo
    try:
        irc_active = cfg["IRC"]["active"]
        irc_fifo = cfg["IRC"]["fifo"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "irc config couldn't be parsed")

    # oncall phone(s) number(s)
    oncallnumbers = []

    try:
        for person in cfg["Astreinte"]:
            oncallnumbers.append(cfg["Annuaire"][person])
    except KeyError:
        syslog.syslog(syslog.LOG_ERR,
                      "Config is wrong for the person(s) or their number(s)")

    return oncallnumbers


if __name__ == "__main__":
    # in case there's number1 and number2
    oncallnumbers = []
    # file may be chmod 000 because of the hack muteSMS_5m.sh
    try:
        oncallnumbers = readconf()
        # what we got in stdin contains newlines
        alertlines = []
        for line in sys.stdin:
            alertlines.append(line)
        alerttosend = ''.join(alertlines)
        # now we have everything so process the alert
        for oncallnumber in oncallnumbers:
            decide_alerting(oncallnumber, alerttosend[0:156])
    # if we can't read the phone number file, alerts must have been disabled
    except IOError:
        syslog.syslog(syslog.LOG_ERR, "Config file couldn't be opened")
