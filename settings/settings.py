__author__ = 'henla464'

from datamodel.datamodel import NodeSettingsData
from datamodel.db_helper import DatabaseHelper

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    configurationDirty = False
    scanForNewRadiosRequest = False

    def __init__(self):
        self.UpdateFromDatabase()

    def GetHWVersion(self):
        return ""

    def SetHWVersion(self, hwVersion):
        return hwVersion

    def UpdateFromDatabase(self):
        self.radioSettings = DatabaseHelper.get_radio_settings_data()
        self.mainSettings = DatabaseHelper.get_main_settings_data()

    @staticmethod
    def SetConfigurationDirty(val=True):
        SettingsClass.configurationDirty = val

    @staticmethod
    def GetIsConfigurationDirty():
        return SettingsClass.configurationDirty

    @staticmethod
    def SetScanForNewRadiosRequest(val=True):
        SettingsClass.scanForNewRadiosRequest = val

    @staticmethod
    def GetScanForNewRadiosRequest():
        return SettingsClass.scanForNewRadiosRequest

    def GetRadioChannel(self, radioNumber):
        for radioSetting in self.radioSettings:
            if radioSetting.RadioNumber == radioNumber:
                channelId = radioSetting.ChannelId
                return DatabaseHelper.get_channel(channelId)
        return None

    def GetRadioMode(self, radioNumber):
        for radioSetting in self.radioSettings:
            if radioSetting.RadioNumber == radioNumber:
                return radioSetting.RadioMode
        return None

    def GetRadioEnabled(self, radioNumber):
        for radioSetting in self.radioSettings:
            if radioSetting.RadioNumber == radioNumber:
                return radioSetting.Enabled
        return None

    def GetInboundRadioNodes(self, radioNumber):
        for radioSetting in self.radioSettings:
            if radioSetting.RadioNumber == radioNumber:
                return radioSetting.InboundRadioNodes
        return None

    def GetSendToMeosDatabase(self):
        return self.mainSettings.SendToMeosDatabase

    def GetMeosDatabaseServer(self):
        return self.mainSettings.MeosDatabaseServer

    def GetMeosDatabaseServerPort(self):
        return self.mainSettings.MeosDatabaseServerPort

    def GetNodeNumber(self):
        return self.mainSettings.NodeNumber