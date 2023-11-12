from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from battery import Battery
import logging
import time
from datetime import datetime, timedelta


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

            statusIntervalSeconds: int = SettingsClass.GetStatusMessageInterval()
            endTime: datetime = datetime.now()
            startTime: datetime = endTime - timedelta(seconds=statusIntervalSeconds)

            noOfLoraMsgSentNotAcked: int = DatabaseHelper.get_no_of_lora_messages_sent_not_acked(startTime, endTime)
            allLoraPunchesSucceded: bool = DatabaseHelper.get_if_all_lora_punches_succeeded(startTime, endTime)

            msgStatus = LoraRadioMessageCreator.GetStatusMessage(Battery.GetIsBatteryLow(), noOfLoraMsgSentNotAcked, allLoraPunchesSucceded)

            self.WiRocLogger.debug("CreateStatusAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": "Status", "MessageSource": "Status", "Data": msgStatus.GetByteArray(), "ChecksumOK": True}

    def AddedToMessageBox(self, mbid):
        return None
