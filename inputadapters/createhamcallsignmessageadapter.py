from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.db_helper import DatabaseHelper
from settings.settings import SettingsClass
from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from battery import Battery
import logging
import time
from datetime import datetime, timedelta


class CreateHAMCallSignMessageAdapter(object):
    Instances = []

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if SettingsClass.GetChannel().startswith("HAM"):
            if len(CreateHAMCallSignMessageAdapter.Instances) == 0:
                CreateHAMCallSignMessageAdapter.Instances.append(CreateHAMCallSignMessageAdapter("hamcs1"))
                return True
        else:
            if len(CreateHAMCallSignMessageAdapter.Instances) > 0:
                CreateHAMCallSignMessageAdapter.Instances = []
                return True
        return False

    @staticmethod
    def GetTypeName():
        return "HAMCS"

    def __init__(self, instanceName):
        self.WiRocLogger = logging.getLogger('WiRoc.Input')
        self.instanceName = instanceName
        self.isInitialized = False
        self.hasCreatedAHamMessage = False
        self.TimeToFetch = False
        self.LastTimeCreated = time.monotonic()

    def GetInstanceName(self) -> str:
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
        if self.hasCreatedAHamMessage:
            currentTime = time.monotonic()
            self.TimeToFetch = (currentTime - self.LastTimeCreated > SettingsClass.GetHAMCallSignMessageInterval())
        else:
            # Should always send a Ham message in tbe beginning of a transmission
            self.TimeToFetch = True
        return self.TimeToFetch

    def GetData(self):
        if self.TimeToFetch:
            self.LastTimeCreated = time.monotonic()
            self.TimeToFetch = False
            self.hasCreatedAHamMessage = True

            HAMCallSign: str = SettingsClass.GetHAMCallSign()

            msgHAMCallSign = LoraRadioMessageCreator.GetHAMCallSignMessage(HAMCallSign)

            self.WiRocLogger.debug("CreateHAMCallSignMessageAdapter::GetData() Data to fetch")
            return {"MessageType": "DATA", "MessageSubTypeName": "Hamcs", "MessageSource": "Ham", "Data": msgHAMCallSign.GetByteArray(), "ChecksumOK": True}

    def AddedToMessageBox(self, mbid):
        return None
