import unittest
import evonitoring


class TestEvonitoring(unittest.TestCase):

    def test_readconf(self):
        oncallnumbers, cfg = evonitoring.readconf()
        # api_cfg
        self.assertEqual(evonitoring.api_cfg["twilio_available_number"],
                         "+14385556677")
        self.assertEqual(evonitoring.api_cfg["pushover_user"], "johndoe")
        self.assertEqual(evonitoring.api_cfg["mobyt_sender"],
                         "33609876543")
        self.assertEqual(evonitoring.api_cfg["smsmode_pass"],
                         "mcpasswordface")
        self.assertEqual(evonitoring.api_cfg["irc_fifo"], "test")
        # cfg
        self.assertTrue(cfg["pushover_active"])
        self.assertTrue(cfg["irc_active"])
        self.assertEqual(cfg["FR_sender"], "smsmode")
        # oncallnumbers
        self.assertIsInstance(oncallnumbers, list)
        self.assertEqual(''.join(oncallnumbers[0]), "33612345678")

    def test_decide_alerting(self):
        oncallnumbers, cfg = evonitoring.readconf()
        self.assertEqual(evonitoring.decide_alerting("33612345678", cfg),
                         "smsmode")
        self.assertEqual(evonitoring.decide_alerting("14381234567", cfg),
                         "twilio")
        self.assertEqual(evonitoring.decide_alerting("15140987654", cfg),
                         "twilio")


if __name__ == '__main__':
    unittest.main()
