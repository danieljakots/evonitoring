import unittest
import evonitoring

class TestEvonitoring(unittest.TestCase):

    def test_readconf(self):
        evonitoring.readconf()
        self.assertEqual(evonitoring.cfg["twilio_available_number"],
                         "+14385556677")
        self.assertEqual(evonitoring.cfg["pushover_active"], "True")
        self.assertEqual(evonitoring.cfg["FR_sender"], "smsmode")
        self.assertEqual(evonitoring.cfg["mobyt_sender"], "33609876543")
        self.assertEqual(evonitoring.cfg["smsmode_pass"], "mcpasswordface")
        self.assertEqual(evonitoring.cfg["irc_active"], "True")


if __name__ == '__main__':
    unittest.main()
