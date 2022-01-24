from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
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
            if len(CreateStatusAdapter.Instances) > 0:
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
        currentTime = time.monotonic()
        self.TimeToFetch = (currentTime - self.LastTimeCreated > SettingsClass.GetStatusMessageInterval())
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.LastTimeCreated = time.monotonic()
            self.TimeToFetch = False
            msgStatus = LoraRadioMessageCreator.GetStatusMessage(Battery.GetIsBatteryLow())

            self.WiRocLogger.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": "Status", "MessageSource": "Status", "Data": msgStatus.GetByteArray(), "ChecksumOK": True}

    def AddedToMessageBox(self, mbid):
        return None
