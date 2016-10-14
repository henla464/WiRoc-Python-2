__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    configurationDirty = False


    @staticmethod
    def SetConfigurationDirty(val=True):
        SettingsClass.configurationDirty = val

    @staticmethod
    def GetIsConfigurationDirty():
        return SettingsClass.configurationDirty

    @staticmethod
    def GetRadioChannel(self, radioNumber):
#        for radioSetting in self.radioSettings:
#            if radioSetting.RadioNumber == radioNumber:
#                channelId = radioSetting.ChannelId
#                return DatabaseHelper.get_channel(channelId)
        return None

    @staticmethod
    def GetChannel():
        sett = DatabaseHelper.get_setting_by_key('Channel');
        if sett is None:
            return 1
        else:
            return int(sett.Value)

    @staticmethod
    def GetDataRate():
        sett = DatabaseHelper.get_setting_by_key('DataRate');
        if sett is None:
            return 586
        else:
            return int(sett.Value)

    @staticmethod
    def GetAcknowledgementRequested():
        sett = DatabaseHelper.get_setting_by_key('AcknowledgementRequested');
        if sett is None:
            return False
        else:
            return sett.Value.lower() == "true"

    @staticmethod
    def GetSendToMeosEnabled():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosEnabled');
        if sett is None:
            return False
        else:
            print(sett.Value)
            return sett.Value == "True"

    @staticmethod
    def GetSendToMeosIP():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosIP');
        if sett is None:
            return None
        else:
            return sett.Value

    @staticmethod
    def GetSendToMeosIPPort():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosIPPort');
        if sett is None:
            return 5000
        else:
             try:
                 return int(sett.Value)
             except ValueError:
                 return 5000
