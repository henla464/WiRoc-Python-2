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
        logging.info("1")
        if len(SendToBlenoAdapter.Instances) > 0:
            enabled = SettingsClass.GetSendToBlenoEnabled()
            isInitialized = SendToBlenoAdapter.Instances[0].GetIsInitialized()
            logging.info("2" + str(SettingsClass.GetSendToBlenoEnabled()))
            logging.info("3" + str(isInitialized))
            if SendToBlenoAdapter.SubscriptionsEnabled != (isInitialized and enabled):
                logging.info("SendToBlenoAdapter subscription set enabled: " + str(isInitialized and enabled))
                SendToBlenoAdapter.SubscriptionsEnabled = (isInitialized and enabled)
                DatabaseHelper.mainDatabaseHelper.set_subscriptions_enabled((isInitialized and enabled), SendToBlenoAdapter.GetTypeName())


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

    def GetDeleteAfterSent(self):
        return True

    def GetIsInitialized(self):
        return self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        #, "SIToMeosTransform", "BLEToMeosTransform"
        return ["SIToSITransform" ]

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
        blenoPunchData.TwelveHourTime = (punchData.TwelveHourTime[0] << 8) + punchData.TwelveHourTime[1]
        blenoPunchData.SubSecond = punchData.SubSecond
        DatabaseHelper.mainDatabaseHelper.save_bleno_punch_data(blenoPunchData)
        return True
