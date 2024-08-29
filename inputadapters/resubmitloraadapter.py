from functools import partial

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import MessageBoxArchiveData
from datamodel.db_helper import DatabaseHelper
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from battery import Battery
import logging
import time
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from threading import RLock

resubmitCache = TTLCache(maxsize=2, ttl=300)  # 300 seconds
rlock = RLock()


class ResubmitLoraAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(ResubmitLoraAdapter.Instances) == 0 and (SettingsClass.GetLoraMode() == "SENDER" or SettingsClass.GetLoraMode() == "REPEATER"):
            ResubmitLoraAdapter.Instances.append(ResubmitLoraAdapter("resubmit1"))
            return True
        else:
            if len(ResubmitLoraAdapter.Instances) > 0 and (SettingsClass.GetLoraMode() == "RECEIVER"):
                ResubmitLoraAdapter.Instances.clear()
                return True
        return False

    @staticmethod
    def GetTypeName():
        return "RESUBMIT"

    def __init__(self, instanceName):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetch = False
        self.LastTimeFetched = time.monotonic()

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

    @cached(resubmitCache, key=partial(hashkey, 'GetResubmitInterval'), lock=rlock)
    def GetResubmitRetryInterval(self):
        totalRetryDelay = SettingsClass.GetTotalRetryDelaySeconds()
        return totalRetryDelay

    def UpdateInfrequently(self):
        currentTime = time.monotonic()
        self.TimeToFetch = (currentTime - self.LastTimeFetched > self.GetResubmitRetryInterval())
        self.WiRocLogger.debug(f"ResubmitLoraAdapter::UpdateInfrequently() time to fetch: {self.TimeToFetch} currentTime: {currentTime} lastTimeFetched: {self.LastTimeFetched} resubmitRetryInterval: {self.GetResubmitRetryInterval()}")
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            currentTime = time.monotonic()
            self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() time to fetch!, currentTime: {currentTime} timeOfLastPunchMessageSentToLora: {SettingsClass.GetTimeOfLastPunchMessageSentToLora()} 2*resubmitRetryInterval: {2*self.GetResubmitRetryInterval()}")
            self.TimeToFetch = False
            if currentTime - SettingsClass.GetTimeOfLastPunchMessageSentToLora() > 2*self.GetResubmitRetryInterval():
                # Only resubmit it if it has gone 2*resubmitretryintervals since last lora punch message was sent
                self.LastTimeFetched = currentTime
                endTime: datetime = datetime.now()
                startTime: datetime = endTime - timedelta(seconds=1800)  # 30 minutes ago

                self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() startTime: {startTime} endTime: {endTime}")
                messageBoxArchiveDatas: list[MessageBoxArchiveData] = DatabaseHelper.get_failed_lora_messages(startTime, endTime)
                self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() len(messageBoxArchiveDatas): {len(messageBoxArchiveDatas)}")
                if len(messageBoxArchiveDatas) == 0:
                    return None
                messageBoxArchiveData = messageBoxArchiveDatas[0]

                noOfSubmitted = DatabaseHelper.get_no_of_times_message_data_submitted_since_last_acked_message(messageBoxArchiveData.MessageData)
                if noOfSubmitted < 4:
                    # need to mark as resubmitted so it is not picked up again
                    DatabaseHelper.set_message_resubmitted(messageBoxArchiveData.id)

                    self.WiRocLogger.debug("ResubmitLoraAdapter::GetData() Data to fetch")
                    return {"MessageType": "DATA", "MessageSubTypeName": messageBoxArchiveData.MessageSubTypeName, "MessageSource": "Resumbmit", "TypeName": messageBoxArchiveData.MessageTypeName, "Data": messageBoxArchiveData.MessageData, "ChecksumOK": True}
                else:
                    # Already submitted 4 times since last acked message so give up. Might be submitted again if a new message is acked.
                    return None
            return None
        return None

    def AddedToMessageBox(self, mbid):
        return None
