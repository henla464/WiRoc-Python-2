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
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetch = False
        self.loraRadioMessage = LoraRadioMessage(payloadDataLength = 0, messageType = LoraRadioMessage.MessageTypeStatus, batteryLow = False, ackReq = False)

    def GetInstanceName(self):
        return self.instanceName

    def GetIsInitialized(self):
        return self.isInitialized

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def UpdateInfreqently(self):
        currentTime = time.monotonic()
        self.TimeToFetch = (currentTime - SettingsClass.GetTimeOfLastMessageAdded() > SettingsClass.GetStatusMessageInterval())
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.TimeToFetch = False
            self.loraRadioMessage.SetBatteryLowBit(Battery.GetIsBatteryLow())
            self.loraRadioMessage.UpdateChecksum()
            logging.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "Data": self.loraRadioMessage.GetByteArray(), "ChecksumOK": True}