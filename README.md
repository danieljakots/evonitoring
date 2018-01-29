# evonitoring.py

This script is used to receive an alert on *stdin* and then send it
with the configured alerting system to the configured number(s). In
addition to text messages, it supports Pushover and irc notifications.

`evonitoring.yml` is a configuration example.

The scripts supports:
* [Twilio](https://www.twilio.com/sms)
* [Mobyt](http://www.mobyt.it/en/send-sms-globally.php)
* [Smsmode](https://www.smsmode.com/solutions-sms/)
* [Pushover](https://pushover.net/)
* [IRC](https://en.wikipedia.org/wiki/Internet_Relay_Chat) but you'll
  need [ii](https://tools.suckless.org/ii/)

It will log to syslog with either INFO priority or ERR (in case of
failure). The goal is that the script never fails, if it encounters an
error, it logs it and then continue the best it can.

You need python-requests and python-yaml (Debian) or py-requests and
py-yaml (OpenBSD). For now python2 is the goal but keeping in mind
python3 is important.


Before committing, make sure than `test_evonitoring.py` is OK and run flake8.
