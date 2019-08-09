from datamodel.datamodel import SIMessage
from datamodel.db_helper import DatabaseHelper
from utils.utils import Utils
from struct import *
import logging

class ReceiveTestPunchesAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
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
        self.TimeToFetch = False
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

    def UpdateInfreqently(self):
        self.TimeToFetch = True
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.TimeToFetch = False
            punchToAdd = DatabaseHelper.get_test_punch_to_add()
            if punchToAdd is not None:
                self.LastPunchIdAdded = punchToAdd.id
                siMessage = SIMessage()
                siMessage.AddHeader(SIMessage.SIPunch)
                stationCode = 999
                subSecond = 0
                payload = bytearray(pack(">HIcHcccc", stationCode,
                                                Utils.EncodeCardNr(punchToAdd.SICardNumber),
                                                bytes([punchToAdd.TwentyFourHour]),
                                                punchToAdd.TwelveHourTimer,
                                                bytes([subSecond]),
                                                bytes([0x00]), #mem2
                                                bytes([0x00]), #mem1
                                                bytes([0x00])  #mem0
                                         ))
                siMessage.AddPayload(payload)
                siMessage.AddFooter()

                logging.debug("ReceiveTestPunchesAdapter::GetData() Data to fetch")
                logging.debug("ReceiveTestPunchesAdapter::GetData() Data to fetch: " + Utils.GetDataInHex(siMessage.GetByteArray(), logging.DEBUG))
                return {"MessageType": "DATA", "MessageSource":"Test", "MessageSubTypeName": "Test", "Data": siMessage.GetByteArray(), "ChecksumOK": True, "MessageID": siMessage.GetMessageID(0)}
        return None

    def AddedToMessageBox(self, mbid):
        DatabaseHelper.set_test_punch_added_to_message_box(mbid, self.LastPunchIdAdded)
        return None