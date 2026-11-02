__author__ = 'henla464'

import unittest
from unittest import mock

from loraradio.LoraRadioRAK3172 import LoraRadioRAK3172

# Run with env/bin/python3 -m unittest loraradio/TestLoraRadioRAK3172.py


class TestLoraRadioRAK3172(unittest.TestCase):

    def test_IsReadyToSend_staleBusyFlag(self):
        class FakeHW:
            busy = True

            def GetIsTransmittingReceiving(self) -> bool:
                return self.busy

        hw = FakeHW()
        radio = LoraRadioRAK3172.__new__(LoraRadioRAK3172)
        radio.hardwareAbstraction = hw
        radio.busySince = None
        radio.staleBusyLogged = False
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=100.0):
            self.assertFalse(radio.IsReadyToSend())  # AUX goes low, clock starts
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=129.0):
            self.assertFalse(radio.IsReadyToSend())  # still within the worst-case airtime
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=131.0):
            with self.assertLogs("WiRoc", level="ERROR"):
                self.assertTrue(radio.IsReadyToSend())  # stale flag, send allowed and logged
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=132.0):
            with self.assertNoLogs("WiRoc", level="ERROR"):
                self.assertTrue(radio.IsReadyToSend())  # logged once per episode
        hw.busy = False
        self.assertTrue(radio.IsReadyToSend())
        self.assertIsNone(radio.busySince)


if __name__ == '__main__':
    unittest.main()
