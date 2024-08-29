from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import SIMessage
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from struct import *
import logging


class ReceiveTestPunchesAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Input')
    Instances = []
    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(ReceiveTestPunchesAdapter.Instances) == 0:
            ReceiveTestPunchesAdapter.Instances.append(ReceiveTestPunchesAdapter("test1"))
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "SITEST"

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetchCounter = 0
        self.LastPunchIdAdded = None

    def GetInstanceName(self):
        return self.instanceName

    def GetIsInitialized(self):
        return self.isInitialized

    def ShouldBeInitialized(self):
        return not self.isInitialized

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def UpdateInfrequently(self):
        return True

    def GetData(self):
        self.TimeToFetchCounter += 1
        if self.TimeToFetchCounter == 10:
            self.TimeToFetchCounter = 0
            punchToAdd = DatabaseHelper.get_test_punch_to_add()
            if punchToAdd is not None:
                self.LastPunchIdAdded = punchToAdd.id
                siMessage = SIMessage()
                siMessage.AddHeader(SIMessage.SIPunch)
                stationCode = 511
                subSecond = punchToAdd.SubSecond
                payload = bytearray(pack(">HIcHcccc", stationCode,
                                    Utils.EncodeCardNr(punchToAdd.SICardNumber),
                                    bytes([punchToAdd.TwentyFourHour]),
                                    punchToAdd.TwelveHourTimer,
                                    bytes([subSecond]),
                                    bytes([0x00]),  # mem2
                                    bytes([0x00]),  # mem1
                                    bytes([0x00])   # mem0
                                ))
                siMessage.AddPayload(payload)
                siMessage.AddFooter()

                ReceiveTestPunchesAdapter.WiRocLogger.debug("ReceiveTestPunchesAdapter::GetData() Data to fetch: " + Utils.GetDataInHex(siMessage.GetByteArray(), logging.DEBUG))
                return {"MessageType": "DATA", "MessageSource": "Test", "MessageSubTypeName": "Test", "Data": siMessage.GetByteArray(), "ChecksumOK": True}
        return None

    def AddedToMessageBox(self, mbid):
        DatabaseHelper.set_test_punch_added_to_message_box(mbid, self.LastPunchIdAdded)
        return None
