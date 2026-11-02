__author__ = 'henla464'

import unittest
from unittest import mock

from datamodel.db_helper import ChannelData
from loraradio.LoraRadioRAK3172 import LoraRadioRAK3172

# Run with env/bin/python3 -m unittest loraradio/TestLoraRadioRAK3172.py


class TestLoraRadioRAK3172(unittest.TestCase):

    def getChannelData(self) -> ChannelData:
        channelData = ChannelData()
        channelData.Frequency = 869525000
        channelData.SpreadingFactor = 7
        channelData.RfBw = 7
        channelData.LowDatarateOptimize = False
        channelData.CRCOn = True
        return channelData

    def test_BuildLORAP2PParametersCmd_noMesh(self):
        cmd = LoraRadioRAK3172.BuildLORAP2PParametersCmd(self.getChannelData(), 0x16, 1, True, True, True, 8)
        self.assertTrue(cmd.startswith("ATC+P2PM=0:869525000:7:7:1:8:22:0:1:1:"))
        fields = cmd.split("=", 1)[1].rstrip("\r").split(':')
        self.assertEqual(17, len(fields))
        self.assertEqual("1", fields[10])  # drf1268ds compat
        self.assertEqual("1", fields[11])  # send ack
        self.assertEqual("0", fields[12])  # payload length
        self.assertEqual("0", fields[13])  # mesh
        self.assertEqual("0", fields[14])  # active root

    def test_BuildLORAP2PParametersCmd_mesh(self):
        cmd = LoraRadioRAK3172.BuildLORAP2PParametersCmd(self.getChannelData(), 0x16, 1, True, True, True, 8,
                                                         True, True, "A1B2C3D4E5F6")
        fields = cmd.split("=", 1)[1].rstrip("\r").split(':')
        self.assertEqual(17, len(fields))
        self.assertEqual("0", fields[10])  # drf1268ds compat forced off in mesh
        self.assertEqual("1", fields[11])  # send ack written as-is, the mesh firmware ignores it
        self.assertEqual("0", fields[12])
        self.assertEqual("1", fields[13])
        self.assertEqual("1", fields[14])
        self.assertEqual("0", fields[15])  # standby root
        self.assertEqual("A1B2C3D4E5F6", fields[16])

    def test_BuildLORAP2PParametersCmd_standbyRoot(self):
        cmd = LoraRadioRAK3172.BuildLORAP2PParametersCmd(self.getChannelData(), 0x16, 1, True, True, True, 8,
                                                         True, False, "A1B2C3D4E5F6", True)
        fields = cmd.split("=", 1)[1].rstrip("\r").split(':')
        self.assertEqual("1", fields[13])  # mesh
        self.assertEqual("0", fields[14])  # active root
        self.assertEqual("1", fields[15])  # standby root

    def test_BuildLORAP2PParametersCmd_stripsInvalidDeviceID(self):
        # a bad setting must not inject extra separators/commands into the AT command
        cmd = LoraRadioRAK3172.BuildLORAP2PParametersCmd(self.getChannelData(), 0x16, 1, True, True, True, 8,
                                                         True, True, "AA:BB\rATC+RESET")
        self.assertNotIn("\r", cmd.rstrip("\r"))
        fields = cmd.split("=", 1)[1].rstrip("\r").split(':')
        self.assertEqual(17, len(fields))
        self.assertEqual("", fields[16])

    def test_GetEffectiveMeshFlags(self):
        # A promoted standby (module is root) survives an incidental re-init
        self.assertEqual((True, False), LoraRadioRAK3172.GetEffectiveMeshFlags(False, True, True, False))
        # A node configured as standby gets the standby config
        self.assertEqual((False, True), LoraRadioRAK3172.GetEffectiveMeshFlags(False, True, False, False))
        # Switching an active root to standby forces the standby write so the module demotes
        self.assertEqual((False, True), LoraRadioRAK3172.GetEffectiveMeshFlags(False, True, True, True))
        # Non-standby modes pass their flags through
        self.assertEqual((True, False), LoraRadioRAK3172.GetEffectiveMeshFlags(True, False, True, False))

    def test_ParseLORAP2PParameters_meshOff(self):
        params = LoraRadioRAK3172.ParseLORAP2PParametersResponse(
            "ATC+P2PM=0:869525000:7:7:1:8:22:0:1:1:0:0:0:0:0:0:000000000000")
        self.assertIsNotNone(params)
        self.assertEqual(869525000, params.Frequency)
        self.assertEqual(7, params.SpreadingFactor)
        self.assertEqual(False, params.MeshEnabled)
        self.assertEqual("000000000000", params.NodeDeviceID)

    def test_ParseLORAP2PParameters_mesh(self):
        params = LoraRadioRAK3172.ParseLORAP2PParametersResponse(
            "ATC+P2PM=0:869525000:7:7:1:8:22:0:1:1:0:0:0:1:1:0:A1B2C3D4E5F6")
        self.assertIsNotNone(params)
        self.assertEqual(True, params.MeshEnabled)
        self.assertEqual(True, params.ActiveRoot)
        self.assertEqual(False, params.StandbyRoot)
        self.assertEqual("A1B2C3D4E5F6", params.NodeDeviceID)

    def test_ParseFeatures(self):
        features = LoraRadioRAK3172.ParseFeaturesResponse("ATC+FEATURES=1:1:1:1")
        self.assertEqual({"p2p": True, "widechannels": True, "narrowchannels": True, "mesh": True}, features)
        # Unknown trailing fields are ignored so newer firmware can append features
        self.assertFalse(LoraRadioRAK3172.ParseFeaturesResponse("ATC+FEATURES=1:1:1:0:1")["mesh"])
        self.assertIsNone(LoraRadioRAK3172.ParseFeaturesResponse("AT_COMMAND_NOT_FOUND"))
        self.assertIsNone(LoraRadioRAK3172.ParseFeaturesResponse("ATC+FEATURES=1:1:1"))

    def test_ParseLegacyLORAP2PParameters(self):
        # Old main/master firmware replies without the selector and without mesh fields
        params = LoraRadioRAK3172.ParseLegacyLORAP2PParametersResponse(
            "ATC+P2P=869525000:7:7:1:8:22:0:1:1:1:1:0")
        self.assertIsNotNone(params)
        self.assertEqual(869525000, params.Frequency)
        self.assertEqual(False, params.MeshEnabled)
        self.assertEqual("", params.NodeDeviceID)
        self.assertIsNone(LoraRadioRAK3172.ParseLegacyLORAP2PParametersResponse("AT_COMMAND_NOT_FOUND"))
        self.assertIsNone(LoraRadioRAK3172.ParseLegacyLORAP2PParametersResponse("ATC+P2P=869525000:7"))

    def test_ParseLORAP2PParameters_invalid(self):
        self.assertIsNone(LoraRadioRAK3172.ParseLORAP2PParametersResponse("AT_PARAM_ERROR"))
        self.assertIsNone(LoraRadioRAK3172.ParseLORAP2PParametersResponse("ATC+P2PM=0:869525000:7"))

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
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=108.0):
            self.assertFalse(radio.IsReadyToSend())  # still within the worst-case airtime
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=113.0):
            with self.assertLogs("WiRoc", level="ERROR"):
                self.assertTrue(radio.IsReadyToSend())  # stale flag, send allowed and logged
        with mock.patch("loraradio.LoraRadioRAK3172.time.monotonic", return_value=114.0):
            with self.assertNoLogs("WiRoc", level="ERROR"):
                self.assertTrue(radio.IsReadyToSend())  # logged once per episode
        hw.busy = False
        self.assertTrue(radio.IsReadyToSend())
        self.assertIsNone(radio.busySince)

    def test_ParseMeshState(self):
        state = LoraRadioRAK3172.ParseMeshStateResponse(
            "ATC+MESHSTATE=1:0:5:0:2:0:3:2:5:3:3:7:806:0")
        self.assertIsNotNone(state)
        self.assertEqual(1, state["enabled"])
        self.assertEqual(0, state["isroot"])
        self.assertEqual(5, state["ownaddr"])
        self.assertEqual(2, state["state"])
        self.assertEqual(3, state["parent"])
        self.assertEqual(2, state["hops"])
        self.assertEqual(5, state["cost"])
        self.assertEqual(806, state["ackms"])
        self.assertIsNone(LoraRadioRAK3172.ParseMeshStateResponse("AT_PARAM_ERROR"))
        self.assertIsNone(LoraRadioRAK3172.ParseMeshStateResponse("ATC+MESHSTATE=1:0:5"))
        self.assertIsNone(LoraRadioRAK3172.ParseMeshStateResponse("ATC+MESHSTATE=1:0:5:x:2:0:3:2:5:3:3:7:806:0"))


if __name__ == '__main__':
    unittest.main()
