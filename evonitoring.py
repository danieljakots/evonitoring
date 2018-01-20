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
                     "token": cfg["pushover_token"],
                     "user": cfg["pushover_user"],
                     "message": alert}),
                 {"Content-type": "application/x-www-form-urlencoded"})
    conn.getresponse()


def twilio(oncallnumber, alert):
    payload = {
        'From': cfg["twilio_available_number"],
        'To': "+" + oncallnumber,
        'Body': alert
    }
    # send the text with twilio's api
    p = requests.post("https://api.twilio.com/2010-04-01/Accounts/" +
                      cfg["twilio_account_sid"] + "/Messages",
                      data=payload,
                      auth=(cfg["twilio_account_sid"],
                            cfg["twilio_auth_token"]))
    if p.status_code != 201:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending twilio')
    syslog.syslog('SMS sent with twilio to ' + oncallnumber)


def smsmode(oncallnumber, alert):
    payload = {"numero": oncallnumber,
               "message": alert,
               "pseudo": cfg["smsmode_user"],
               "pass": cfg["smsmode_pass"]}
    g = requests.get("http://" + cfg["smsmode_host"] + "/http/1.6/sendSMS.do",
                     params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending smsmode')
    syslog.syslog('SMS sent with smsmode to ' + oncallnumber)


def mobyt(oncallnumber, alert):
    payload = {"rcpt": "+" + oncallnumber,
               "data": alert,
               "user": cfg["mobyt_user"],
               "pass": cfg["mobyt_pass"],
               "sender": cfg["mobyt_sender"],
               "qty": "n"}
    g = requests.get("http://" + cfg["mobyt_host"] + "/sms/send.php",
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
    with open(cfg["irc_fifo"], "a") as f:
        f.write(''.join(uniline))
    syslog.syslog('Alert sent to irc as well')

# which alerting system should we use: mobyt, twilio
def decide_alerting(oncallnumber, alert):
    if cfg["pushover_active"] == "True":
        # it must not block nor kill the script
        try:
            pushover(alert)
        except:
            pass
    # select the right sender depend of the number
    if oncallnumber[0:2] == "33":
        if cfg["FR_sender"] == "mobyt":
            mobyt(oncallnumber, alert)
        elif cfg["FR_sender"] == "smsmode":
            smsmode(oncallnumber, alert)
        elif cfg["FR_sender"] == "twilio":
            twilio(oncallnumber, alert)
    else:
        twilio(oncallnumber, alert)

    if cfg["irc_active"] == "True":
        # it must not block nor kill the script
        try:
            irc(alert)
        except:
            pass


def readconf():
    with open(CONFIG, 'r') as ymlfile:
        yaml_cfg = yaml.load(ymlfile)

    global cfg
    cfg = {}

    # twilio api key
    try:
        cfg["twilio_account_sid"] = yaml_cfg["Twilio"]["account_sid"]
        cfg["twilio_auth_token"] = yaml_cfg["Twilio"]["auth_token"]
        cfg["twilio_available_number"] = yaml_cfg["Twilio"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Twilio config couldn't be parsed")

    # pushover
    try:
        cfg["pushover_token"] = yaml_cfg["Pushover"]["token"]
        cfg["pushover_user"] = yaml_cfg["Pushover"]["user"]
        cfg["pushover_active"] = yaml_cfg["Pushover"]["active"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Pushover config couldn't be parsed")

    # sender system
    if yaml_cfg["FR-Astreinte-send"] == "mobyt":
        cfg["FR_sender"] = "mobyt"
    elif yaml_cfg["FR-Astreinte-send"] == "smsmode":
        cfg["FR_sender"] = "smsmode"
    elif yaml_cfg["FR-Astreinte-send"] == "twilio":
        cfg["FR_sender"] = "twilio"
    else:
        syslog.syslog(syslog.LOG_ERR,
                      "Config erroneous FR-Astreinte-send is wrong")

    # mobyt
    try:
        cfg["mobyt_ip"] = yaml_cfg["Mobyt"]["ip"]
        cfg["mobyt_port"] = yaml_cfg["Mobyt"]["port"]
        cfg["mobyt_host"] = yaml_cfg["Mobyt"]["host"]
        cfg["mobyt_user"] = yaml_cfg["Mobyt"]["user"]
        cfg["mobyt_pass"] = yaml_cfg["Mobyt"]["pass"]
        cfg["mobyt_sender"] = yaml_cfg["Mobyt"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Mobyt config couldn't be parsed")

    # smsmode
    try:
        cfg["smsmode_ip"] = yaml_cfg["Smsmode"]["ip"]
        cfg["smsmode_port"] = yaml_cfg["Smsmode"]["port"]
        cfg["smsmode_host"] = yaml_cfg["Smsmode"]["host"]
        cfg["smsmode_user"] = yaml_cfg["Smsmode"]["user"]
        cfg["smsmode_pass"] = yaml_cfg["Smsmode"]["pass"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Smsmode config couldn't be parsed")

    # IRC
    try:
        cfg["irc_active"] = yaml_cfg["IRC"]["active"]
        cfg["irc_fifo"] = yaml_cfg["IRC"]["fifo"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "irc config couldn't be parsed")

    # oncall phone(s) number(s)
    oncallnumbers = []

    try:
        for person in yaml_cfg["Astreinte"]:
            oncallnumbers.append(yaml_cfg["Annuaire"][person])
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
