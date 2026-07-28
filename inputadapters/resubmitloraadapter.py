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
        return "RESUBMITLORA"

    def __init__(self, instanceName):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.LastTimeFetched = time.monotonic()
        self._nextResubmitTime: float = 0  # 0 = idle; >0 = earliest monotonic time to try next resubmit

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
        # Adjust to not query database too often but still resubmit often enough
        # GetRetryDelay is in microseconds, return in seconds
        resubmitInterval = SettingsClass.GetRetryDelay(4)
        return resubmitInterval / 1000000

    def UpdateInfrequently(self) -> bool:
        currentTime = time.monotonic()
        if self._nextResubmitTime == 0:
            # Idle: check if enough time has passed since last fetch to start looking for failed messages.
            if currentTime - self.LastTimeFetched > self.GetResubmitRetryInterval():
                self._nextResubmitTime = currentTime  # fetch due now
        # Return True if a resubmit is scheduled (now or future), so the adapter stays
        # in the active list and GetData() is called each loop iteration for its own gating.
        return self._nextResubmitTime != 0

    def GetData(self):
        if self._nextResubmitTime == 0:
            return None

        currentTime = time.monotonic()
        if currentTime < self._nextResubmitTime:
            return None  # not yet due
        
        self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() currentTime: {currentTime} nextResubmitTime: {self._nextResubmitTime} timeOfLastPunchMessageSentToLora: {SettingsClass.GetTimeOfLastPunchMessageSentToLora()}")

        # Clear the scheduled time. Will be re-set below if a resubmit succeeds.
        self._nextResubmitTime = 0

        # Only resubmit if no active LORA messages are currently being sent (not yet acked)
        if DatabaseHelper.any_active_lora_subscriptions_not_acked():
            self.WiRocLogger.debug("ResubmitLoraAdapter::GetData() Skipping resubmit: active LORA message subscriptions are not yet acked")
            return None
        # Don't resubmit if airtime usage is already above 20%
        toaPerc = SettingsClass.GetLoraAirTimePercentage()
        if toaPerc > 20.0:
            self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() Skipping resubmit: airtime percentage is {toaPerc} (too high)")
            return None
        else:
            self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() Airtime percentage is {toaPerc}")

        self.LastTimeFetched = currentTime
        endTime: datetime = datetime.now()
        startTime: datetime = endTime - timedelta(seconds=SettingsClass.GetResubmitLookbackSeconds())

        messageBoxArchiveDatas: list[MessageBoxArchiveData] = DatabaseHelper.get_failed_lora_messages(startTime, endTime)
        self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() startTime: {startTime} endTime: {endTime} Messages exists: {len(messageBoxArchiveDatas) > 0}")
        if len(messageBoxArchiveDatas) == 0:
            return None
        messageBoxArchiveData = messageBoxArchiveDatas[0]

        noOfSubmitted = DatabaseHelper.get_no_of_times_message_data_submitted_since_last_acked_message(messageBoxArchiveData.MessageData)
        if noOfSubmitted < 4:
            # need to mark as resubmitted so it is not picked up again
            DatabaseHelper.set_message_resubmitted(messageBoxArchiveData.id)

            # Schedule next resubmit after GetRetryDelay(1) so more failed messages
            # can be processed quickly without waiting for the next UpdateInfrequently cycle.
            self._nextResubmitTime = currentTime + SettingsClass.GetRetryDelay(1) / 1000000
            self.WiRocLogger.debug(f"ResubmitLoraAdapter::GetData() set nextResubmitTime: {self._nextResubmitTime}")

            self.WiRocLogger.debug("ResubmitLoraAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": messageBoxArchiveData.MessageSubTypeName, 
                    "MessageSource": "ResubmitLora", "TypeName": messageBoxArchiveData.MessageTypeName, 
                    "Data": messageBoxArchiveData.MessageData, "ChecksumOK": True,
                    "LimitToSubscriberTypeName": "LORA"}
        else:
            # Already submitted 4 times since last acked message so give up. Might be submitted again if a new message is acked.
            return None

    def AddedToMessageBox(self, mbid):
        return None
