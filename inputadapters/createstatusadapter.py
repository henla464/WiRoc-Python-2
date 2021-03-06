from settings.settings import SettingsClass
from datamodel.datamodel import LoraRadioMessage
from battery import Battery
import logging
import time

class CreateStatusAdapter(object):
    Instances = []
    @staticmethod
    def CreateInstances():
        if SettingsClass.GetSendStatusMessages():
            if len(CreateStatusAdapter.Instances) == 0:
                CreateStatusAdapter.Instances.append(CreateStatusAdapter("status1"))
                return True
        else:
            if len(CreateStatusAdapter.Instances)>0:
                CreateStatusAdapter.Instances = []
                return True
        return False

    @staticmethod
    def GetTypeName():
        return "STATUS"

    def __init__(self, instanceName):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetch = False
        self.LastTimeCreated = time.monotonic()
        self.loraRadioMessage = LoraRadioMessage(payloadDataLength = 0, messageType = LoraRadioMessage.MessageTypeStatus, batteryLow = False, ackReq = False)

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
        currentTime = time.monotonic()
        self.TimeToFetch = (currentTime - max(SettingsClass.GetTimeOfLastMessageSentToLora(), self.LastTimeCreated) > SettingsClass.GetStatusMessageInterval())
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.LastTimeCreated = time.monotonic()
            self.TimeToFetch = False
            self.loraRadioMessage.SetBatteryLowBit(Battery.GetIsBatteryLow())
            self.loraRadioMessage.UpdateChecksum()
            self.WiRocLogger.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": "Status", "MessageSource":"Status", "Data": self.loraRadioMessage.GetByteArray(), "ChecksumOK": True}

    def AddedToMessageBox(self, mbid):
        return None