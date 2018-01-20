#!/usr/bin/env python2

from __future__ import print_function
import httplib
import sys
import syslog
import urllib

# you need to install py-requests (OpenBSD) or python-requests (Debian)
# you need to install py-yaml     (OpenBSD) or python-yaml     (Debian)
import requests
import yaml

CONFIG = "/etc/evonitoring.yml"


def pushover(alert):
    conn = httplib.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.urlencode({
                     "token": api_cfg["pushover_token"],
                     "user": api_cfg["pushover_user"],
                     "message": alert}),
                 {"Content-type": "application/x-www-form-urlencoded"})
    conn.getresponse()


def twilio(oncallnumber, alert):
    payload = {'From': api_cfg["twilio_available_number"],
               'To': "+" + oncallnumber,
               'Body': alert}
    # send the text with twilio's api
    p = requests.post("https://api.twilio.com/2010-04-01/Accounts/" +
                      api_cfg["twilio_account_sid"] + "/Messages",
                      data=payload,
                      auth=(api_cfg["twilio_account_sid"],
                            api_cfg["twilio_auth_token"]))
    if p.status_code != 201:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending twilio')
    syslog.syslog('SMS sent with twilio to ' + oncallnumber)


def smsmode(oncallnumber, alert):
    payload = {"numero": oncallnumber,
               "message": alert,
               "pseudo": api_cfg["smsmode_user"],
               "pass": api_cfg["smsmode_pass"]}
    g = requests.get("http://" + api_cfg["smsmode_host"] +
                     "/http/1.6/sendSMS.do", params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending smsmode')
    syslog.syslog('SMS sent with smsmode to ' + oncallnumber)


def mobyt(oncallnumber, alert):
    payload = {"rcpt": "+" + oncallnumber,
               "data": alert,
               "user": api_cfg["mobyt_user"],
               "pass": api_cfg["mobyt_pass"],
               "sender": api_cfg["mobyt_sender"],
               "qty": "n"}
    g = requests.get("http://" + api_cfg["mobyt_host"] + "/sms/send.php",
                     params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending mobyt')
    syslog.syslog('SMS sent with mobyt to ' + oncallnumber)


def irc(alert):
    # concat the multiple lines into a single line
    uniline = []
    for l in alert:
        if l == '\n':
            l = ' '
        uniline.append(l)
    uniline.append('\n')
    with open(api_cfg["irc_fifo"], "a") as f:
        f.write(''.join(uniline))
    syslog.syslog('Alert sent to irc as well')


def decide_alerting(oncallnumber, cfg):
    # select the right sender depending of the number
    if oncallnumber[0:2] == "33":
        system = cfg["FR_sender"]
    else:
        system = "twilio"
    return system


def alert(oncallnumber, alert, system, cfg):
    if cfg["pushover_active"] == "True":
        # it must not block nor kill the script
        try:
            pushover(alert)
        except:
            pass
    # use the right alerting system
    if system == "mobyt":
        mobyt(oncallnumber, alert)
    elif system == "smsmode":
        smsmode(oncallnumber, alert)
    elif system == "twilio":
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

    global api_cfg
    api_cfg = {}
    cfg = {}

    # twilio api key
    try:
        api_cfg["twilio_account_sid"] = yaml_cfg["Twilio"]["account_sid"]
        api_cfg["twilio_auth_token"] = yaml_cfg["Twilio"]["auth_token"]
        api_cfg["twilio_available_number"] = yaml_cfg["Twilio"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Twilio config couldn't be parsed")

    # pushover
    try:
        api_cfg["pushover_token"] = yaml_cfg["Pushover"]["token"]
        api_cfg["pushover_user"] = yaml_cfg["Pushover"]["user"]
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
        api_cfg["mobyt_ip"] = yaml_cfg["Mobyt"]["ip"]
        api_cfg["mobyt_port"] = yaml_cfg["Mobyt"]["port"]
        api_cfg["mobyt_host"] = yaml_cfg["Mobyt"]["host"]
        api_cfg["mobyt_user"] = yaml_cfg["Mobyt"]["user"]
        api_cfg["mobyt_pass"] = yaml_cfg["Mobyt"]["pass"]
        api_cfg["mobyt_sender"] = yaml_cfg["Mobyt"]["sender"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Mobyt config couldn't be parsed")

    # smsmode
    try:
        api_cfg["smsmode_ip"] = yaml_cfg["Smsmode"]["ip"]
        api_cfg["smsmode_port"] = yaml_cfg["Smsmode"]["port"]
        api_cfg["smsmode_host"] = yaml_cfg["Smsmode"]["host"]
        api_cfg["smsmode_user"] = yaml_cfg["Smsmode"]["user"]
        api_cfg["smsmode_pass"] = yaml_cfg["Smsmode"]["pass"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Smsmode config couldn't be parsed")

    # IRC
    try:
        cfg["irc_active"] = yaml_cfg["IRC"]["active"]
        api_cfg["irc_fifo"] = yaml_cfg["IRC"]["fifo"]
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

    return oncallnumbers, cfg


if __name__ == "__main__":
    # in case there are multiple numbers
    oncallnumbers = []
    # file may be chmod 000 because of the hack muteSMS_5m.sh
    try:
        oncallnumbers, cfg = readconf()
        # what we got in stdin contains newlines
        alertlines = []
        for line in sys.stdin:
            alertlines.append(line)
        alerttosend = ''.join(alertlines)
        # now we have everything so process the alert
        for oncallnumber in oncallnumbers:
            system = decide_alerting(oncallnumber, cfg)
            alert(oncallnumber, alerttosend[0:156], system, cfg)
    # if we can't read the phone number file, alerts must have been disabled
    except IOError:
        syslog.syslog(syslog.LOG_ERR, "Config file couldn't be opened")
