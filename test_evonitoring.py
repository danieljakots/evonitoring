#!/usr/bin/env python2

import unittest
import evonitoring

config_file = "./evonitoring.yml"


class TestEvonitoring(unittest.TestCase):

    def test_readconf(self):
        oncallnumbers, cfg = evonitoring.readconf(config_file)
        # api_cfg
        self.assertEqual(evonitoring.api_cfg["twilio_api_url"],
                         "https://api.twilio.com/2010-04-01/Accounts/" +
                         evonitoring.api_cfg["twilio_account_sid"] +
                         "/Messages")
        self.assertEqual(evonitoring.api_cfg["pushover_api_url"],
                         "https://api.pushover.net/1/messages.json")
        self.assertEqual(evonitoring.api_cfg["mobyt_api_url"],
                         "http://mobyt.example.com/sms/send.php")
        self.assertEqual(evonitoring.api_cfg["smsmode_api_url"],
                         "http://smsmode.example.com/http/1.6/sendSMS.do")
        self.assertEqual(evonitoring.api_cfg["irc_fifo"], "test")
        # cfg
        self.assertTrue(cfg["pushover_active"])
        self.assertTrue(cfg["irc_active"])
        self.assertEqual(cfg["FR_sender"], "smsmode")
        # oncallnumbers
        self.assertIsInstance(oncallnumbers, list)
        self.assertEqual(''.join(oncallnumbers[0]), "33612345678")

    def test_decide_alerting(self):
        oncallnumbers, _ = evonitoring.readconf(config_file)
        self.assertEqual(evonitoring.decide_alerting("33612345678", cfg),
                         "smsmode")
        self.assertEqual(evonitoring.decide_alerting("14381234567", cfg),
                         "twilio")
        self.assertEqual(evonitoring.decide_alerting("15140987654", cfg),
                         "twilio")

    def test_convert_multiline(self):
        multiline = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit." + "\n"
            "In sodales scelerisque facilisis." + "\n"
            "Vestibulum sit amet mattis leo." + "\n"
        )
        uniline = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "In sodales scelerisque facilisis. "
            "Vestibulum sit amet mattis leo."
            )
        self.assertEqual(evonitoring.convert_multiline(multiline),
                         uniline + "\n")


if __name__ == '__main__':
    unittest.main()
