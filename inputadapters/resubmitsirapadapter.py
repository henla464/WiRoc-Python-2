from functools import partial

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.datamodel import MessageBoxArchiveData
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
import logging
import time
from datetime import datetime, timedelta
from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from threading import RLock

resubmitCache = TTLCache(maxsize=2, ttl=300)  # 300 seconds
rlock = RLock()


class ResubmitSirapAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(ResubmitSirapAdapter.Instances) == 0 and SettingsClass.GetSendToSirapEnabled():
            ResubmitSirapAdapter.Instances.append(ResubmitSirapAdapter("resubmitsirap1"))
            return True
        elif len(ResubmitSirapAdapter.Instances) > 0 and not SettingsClass.GetSendToSirapEnabled():
            ResubmitSirapAdapter.Instances.clear()
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "RESUBMITSIRAP"

    def __init__(self, instanceName):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.TimeToFetch = False
        self.LastTimeFetched = time.monotonic()
        self.resubmitInterval = 1

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

    def UpdateInfrequently(self) -> bool:
        self.TimeToFetch = True
        return True

    def GetData(self):
        # TimeToFetch is set true every ~10s, and when last sirap message was successful
        # and there was a message to submit
        if not self.TimeToFetch:
            return None

        currentTime = time.monotonic()
        if currentTime - self.LastTimeFetched < self.resubmitInterval:
            return None
        
        self.TimeToFetch = False

        # Don't resubmit if there are active SIRAP subscriptions being processed
        if DatabaseHelper.any_active_sirap_subscriptions():
            self.WiRocLogger.debug("ResubmitSirapAdapter::GetData() Skipping: active SIRAP subscriptions exist")
            return None

        self.LastTimeFetched = currentTime
        endTime: datetime = datetime.now()
        startTime: datetime = endTime - timedelta(seconds=SettingsClass.GetResubmitLookbackSeconds())

        self.WiRocLogger.debug(f"ResubmitSirapAdapter::GetData() startTime: {startTime} endTime: {endTime}")
        messageBoxArchiveDatas: list[MessageBoxArchiveData] = DatabaseHelper.get_failed_sirap_messages(startTime, endTime)
        self.WiRocLogger.debug(f"ResubmitSirapAdapter::GetData() Messages exists: {len(messageBoxArchiveDatas) > 0}")
        if len(messageBoxArchiveDatas) == 0:
            return None
        else:
            # We have a message to resubmit
            # If last sirap message was successful then check for more messages
            # to resubmit in self.resubmitInterval s
            if not DatabaseHelper.last_sirap_subscription_failed():
                self.TimeToFetch = True

        messageBoxArchiveData = messageBoxArchiveDatas[0]

        noOfSubmitted = DatabaseHelper.get_no_of_times_sirap_message_submitted_since_last_successful_sirap(messageBoxArchiveData.MessageData)
        if noOfSubmitted < 4:
            # need to mark as resubmitted so it is not picked up again
            DatabaseHelper.set_message_resubmitted(messageBoxArchiveData.id, 'SIRAP')

            self.WiRocLogger.debug("ResubmitSirapAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": messageBoxArchiveData.MessageSubTypeName,
                    "MessageSource": "ResubmitSirap", "TypeName": messageBoxArchiveData.MessageTypeName,
                    "Data": messageBoxArchiveData.MessageData, "ChecksumOK": True,
                    "LimitToSubscriberTypeName": "SIRAP"}
        else:
            # Already submitted 4 times, give up
            return None

    def AddedToMessageBox(self, mbid):
        return None
