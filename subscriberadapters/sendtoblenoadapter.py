from settings.settings import SettingsClass
from datamodel.datamodel import BlenoPunchData
from datamodel.db_helper import DatabaseHelper
from utils.utils import PunchData
import logging

class SendToBlenoAdapter(object):
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances():
        if len(SendToBlenoAdapter.Instances) == 0:
            SendToBlenoAdapter.Instances.append(SendToBlenoAdapter('bleno1'))

        return SendToBlenoAdapter.Instances

    @staticmethod
    def GetTypeName():
        return "BLENO"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToBlenoAdapter.Instances) > 0:
            enabled = SettingsClass.GetSendToBlenoEnabled()
            isInitialized = SendToBlenoAdapter.Instances[0].GetIsInitialized()
            if SendToBlenoAdapter.SubscriptionsEnabled != (isInitialized and enabled):
                logging.info("SendToBlenoAdapter subscription set enabled: " + str(isInitialized and enabled))
                SendToBlenoAdapter.SubscriptionsEnabled = (isInitialized and enabled)
                DatabaseHelper.mainDatabaseHelper.update_subscriptions((isInitialized and enabled), SendToBlenoAdapter.GetDeleteAfterSent(), SendToBlenoAdapter.GetTypeName())


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

    def GetIsInitialized(self):
        return self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        return ["SIToSITransform", "LoraToSITransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    # messageData is a bytearray
    def SendData(self, messageData):
        punchData = PunchData(messageData)
        blenoPunchData = BlenoPunchData()
        blenoPunchData.StationNumber = punchData.StationNumber
        blenoPunchData.SICardNumber = punchData.SICardNumber
        blenoPunchData.TwentyFourHour = punchData.TwentyFourHour
        blenoPunchData.TwelveHourTimer = (punchData.TwelveHourTimer[0] << 8) + punchData.TwelveHourTimer[1]
        blenoPunchData.SubSecond = punchData.SubSecond
        DatabaseHelper.mainDatabaseHelper.save_bleno_punch_data(blenoPunchData)
        return True
