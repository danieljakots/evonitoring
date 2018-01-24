#!/usr/bin/env python2

from __future__ import print_function
import sys
import syslog

# you need to install py-requests (OpenBSD) or python-requests (Debian)
# you need to install py-yaml     (OpenBSD) or python-yaml     (Debian)
import requests
import yaml

CONFIG_FILE = "/etc/evonitoring.yml"


def notify_pushover(alert):
    """Send a pushover notification."""
    payload = {"token": api_cfg["pushover_token"],
               "user": api_cfg["pushover_user"],
               "message": alert}

    requests.post(api_cfg["pushover_api_url"], params=payload)


def notify_twilio(oncallnumber, alert):
    """Send a text with twilio."""
    payload = {'From': api_cfg["twilio_available_number"],
               'To': "+" + oncallnumber,
               'Body': alert}
    # send the text with twilio's api
    p = requests.post(api_cfg["twilio_api_url"] +
                      api_cfg["twilio_account_sid"] + "/Messages",
                      data=payload,
                      auth=(api_cfg["twilio_account_sid"],
                            api_cfg["twilio_auth_token"]))
    if p.status_code != 201:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending twilio')
    syslog.syslog('SMS sent with twilio to ' + oncallnumber)


def notify_smsmode(oncallnumber, alert):
    """Send a text with smsmode."""
    payload = {"numero": oncallnumber,
               "message": alert,
               "pseudo": api_cfg["smsmode_user"],
               "pass": api_cfg["smsmode_pass"]}
    g = requests.get(api_cfg["smsmode_api_url"], params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending smsmode')
    syslog.syslog('SMS sent with smsmode to ' + oncallnumber)


def notify_mobyt(oncallnumber, alert):
    """Send a text with mobyt."""
    payload = {"rcpt": "+" + oncallnumber,
               "data": alert,
               "user": api_cfg["mobyt_user"],
               "pass": api_cfg["mobyt_pass"],
               "sender": api_cfg["mobyt_sender"],
               "qty": "n"}
    g = requests.get(api_cfg["mobyt_api_url"], params=payload)
    if g.status_code != 200:
        syslog.syslog(syslog.LOG_ERR, 'Problem while sending mobyt')
    syslog.syslog('SMS sent with mobyt to ' + oncallnumber)


def notify_irc(alert):
    """Send a message to file which is actually a gateway to irc."""
    with open(api_cfg["irc_fifo"], "a") as f:
        f.write(convert_multiline(alert))
    syslog.syslog('Alert sent to irc as well')


def convert_multiline(text):
    """Convert a multi-line string to one-line one."""
    oneline = " ".join(text.splitlines()) + "\n"
    return oneline


def decide_alerting(oncallnumber, cfg):
    """Return the text provider to use depending on the conf and the number."""
    # select the right sender depending of the number
    if oncallnumber[0:2] == "33":
        notify_system = cfg["FR_sender"]
    else:
        notify_system = "twilio"
    return notify_system


def alert(oncallnumber, alert, notify_system, cfg):
    """Call the chosen system(s) to send the alert."""
    # first class citizen
    try:
        if notify_system == "mobyt":
            notify_mobyt(oncallnumber, alert)
        elif notify_system == "smsmode":
            notify_smsmode(oncallnumber, alert)
        elif notify_system == "twilio":
            notify_twilio(oncallnumber, alert)
    except:
        # we don't fallback on another notify system because there's a whole
        # monitoring system in backup using another provider
        syslog.syslog(syslog.LOG_ERR,
                      "Couldn't call a notify function, check the config file")

    # second class citizen
    if cfg["pushover_active"]:
        # it must not block nor kill the script
        try:
            notify_pushover(alert)
        except:
            pass
    if cfg["irc_active"]:
        # it must not block nor kill the script
        try:
            notify_irc(alert)
        except:
            pass


def readconf(config_file):
    """Parse the configuration file.

    It uses 3 data structures:
    - api_cfg: a global dict that contains the API keys
    - cfg: a *returned* dict with the state (in/active) of irc, pushover
    - oncallnumbers: a *returned* list of numbers to send the alert to

    The policy is to never fail but just log if there's a problem.
    """
    with open(config_file, 'r') as ymlfile:
        yaml_cfg = yaml.load(ymlfile)

    global api_cfg
    api_cfg = {}
    cfg = {}

    # twilio api key
    try:
        api_cfg["twilio_account_sid"] = yaml_cfg["Twilio"]["account_sid"]
        api_cfg["twilio_auth_token"] = yaml_cfg["Twilio"]["auth_token"]
        api_cfg["twilio_available_number"] = yaml_cfg["Twilio"]["sender"]
        api_cfg["twilio_api_url"] = yaml_cfg["Twilio"]["api_url"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Twilio config couldn't be parsed")

    # pushover
    try:
        api_cfg["pushover_token"] = yaml_cfg["Pushover"]["token"]
        api_cfg["pushover_user"] = yaml_cfg["Pushover"]["user"]
        api_cfg["pushover_api_url"] = yaml_cfg["Pushover"]["api_url"]
        if yaml_cfg["Pushover"]["active"] == "True":
            cfg["pushover_active"] = True
        else:
            cfg["pushover_active"] = False
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
        api_cfg["mobyt_user"] = yaml_cfg["Mobyt"]["user"]
        api_cfg["mobyt_pass"] = yaml_cfg["Mobyt"]["pass"]
        api_cfg["mobyt_sender"] = yaml_cfg["Mobyt"]["sender"]
        api_cfg["mobyt_api_url"] = yaml_cfg["Mobyt"]["api_url"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Mobyt config couldn't be parsed")

    # smsmode
    try:
        api_cfg["smsmode_user"] = yaml_cfg["Smsmode"]["user"]
        api_cfg["smsmode_pass"] = yaml_cfg["Smsmode"]["pass"]
        api_cfg["smsmode_api_url"] = yaml_cfg["Smsmode"]["api_url"]
    except KeyError:
        syslog.syslog(syslog.LOG_ERR, "Smsmode config couldn't be parsed")

    # IRC
    try:
        if yaml_cfg["IRC"]["active"] == "True":
            cfg["irc_active"] = True
        else:
            cfg["irc_active"] = False
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
        oncallnumbers, cfg = readconf(CONFIG_FILE)
        # what we got in stdin contains \n but we want it to be a single string
        alertlines = []
        for line in sys.stdin:
            alertlines.append(line)
        alerttosend = ''.join(alertlines)
        # now we have everything so process the alert
        for oncallnumber in oncallnumbers:
            notify_system = decide_alerting(oncallnumber, cfg)
            alert(oncallnumber, alerttosend[0:156], notify_system, cfg)
    # if we can't read the phone number file, alerts must have been disabled
    except IOError:
        syslog.syslog(syslog.LOG_ERR, "Config file couldn't be opened")
