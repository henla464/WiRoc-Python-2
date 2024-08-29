from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.datamodel import BlenoPunchData
from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SIMessage
import logging


class SendToBlenoAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if len(SendToBlenoAdapter.Instances) == 0:
            SendToBlenoAdapter.Instances.append(SendToBlenoAdapter('bleno1'))
            return True
        if SendToBlenoAdapter.SubscriptionsEnabled != SettingsClass.GetSendToBlenoEnabled():
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "BLENO"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToBlenoAdapter.Instances) > 0:
            enabled = SettingsClass.GetSendToBlenoEnabled()
            isInitialized = SendToBlenoAdapter.Instances[0].GetIsInitialized()
            if SendToBlenoAdapter.SubscriptionsEnabled != (isInitialized and enabled):
                SendToBlenoAdapter.WiRocLogger.info("SendToBlenoAdapter subscription set enabled: " + str(isInitialized and enabled))
                SendToBlenoAdapter.SubscriptionsEnabled = (isInitialized and enabled)
                DatabaseHelper.update_subscriptions((isInitialized and enabled), SendToBlenoAdapter.GetDeleteAfterSent(), SendToBlenoAdapter.GetTypeName())


    @staticmethod
    def EnableDisableTransforms():
        return None

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.transforms = {}
        self.isInitialized = False
        self.isDBInitialized = False

    def GetInstanceName(self):
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent():
        return True

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent():
        return False

    def GetIsInitialized(self):
        return self.isInitialized

    def ShouldBeInitialized(self):
        return not self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        return ["SISIMessageToSITransform", "LoraSIMessageToSITransform",
                "LoraSIMessageDoubleToSITransform", "SRRSRRMessageToSITransform",
                "SITestTestToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def IsReadyToSend(self):
        return True

    @staticmethod
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1

    # messageData is a tuple of bytearray
    def SendData(self, messageData, successCB, failureCB, notSentCB, settingsDictionary):
        for data in messageData:
            SIMsg = SIMessage()
            SIMsg.AddPayload(data)
            blenoPunchData = BlenoPunchData()
            blenoPunchData.StationNumber = SIMsg.GetStationNumber()
            blenoPunchData.SICardNumber = SIMsg.GetSICardNumber()
            blenoPunchData.TwentyFourHour = SIMsg.GetTwentyFourHour()
            blenoPunchData.TwelveHourTimer = (SIMsg.GetTwelveHourTimer()[0] << 8) + SIMsg.GetTwelveHourTimer()[1]
            blenoPunchData.SubSecond = SIMsg.GetSubSecondAsTenthOfSeconds()
            DatabaseHelper.save_bleno_punch_data(blenoPunchData)
        successCB()
        return True
