__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    configurationDirty = False
    channel = None
    dataRate = None
    acknowledgementRequested = None
    sendToMeosEnabled = None
    sendToMeosIP = None
    sendToMeosIPPort = None
    powerCycle = None

    @staticmethod
    def SetConfigurationDirty(settingsName=None):
        if settingsName == 'Channel':
            SettingsClass.channel = None
        if settingsName == 'DataRate':
            SettingsClass.dataRate = None
        if settingsName == 'AcknowledgementRequested':
            SettingsClass.acknowledgementRequested = None
        if settingsName == 'SendToMeosEnabled':
            SettingsClass.sendToMeosEnabled = None
        if settingsName == 'SendToMeosIP':
            SettingsClass.sendToMeosIP = None
        if settingsName == 'SendToMeosIPPort':
            SettingsClass.sendToMeosIPPort = None
        if settingsName == 'PowerCycle':
            SettingsClass.powerCycle = None

    @staticmethod
    def GetChannel():
        if SettingsClass.channel is None:
            sett = DatabaseHelper.get_setting_by_key('Channel')
            if sett is None:
                SettingsClass.channel = 1
            else:
                SettingsClass.channel = int(sett.Value)
        return SettingsClass.channel

    @staticmethod
    def GetDataRate():
        if SettingsClass.dataRate is None:
            sett = DatabaseHelper.get_setting_by_key('DataRate')
            if sett is None:
                SettingsClass.dataRate = 586
            else:
                SettingsClass.dataRate = int(sett.Value)
        return SettingsClass.dataRate

    @staticmethod
    def GetAcknowledgementRequested():
        if SettingsClass.acknowledgementRequested is None:
            sett = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
            if sett is None:
                SettingsClass.acknowledgementRequested = False
            else:
                SettingsClass.acknowledgementRequested = (sett.Value.lower() == "true")
        return SettingsClass.acknowledgementRequested

    @staticmethod
    def GetSendToMeosEnabled():
        if SettingsClass.sendToMeosEnabled is None:
            sett = DatabaseHelper.get_setting_by_key('SendToMeosEnabled')
            if sett is None:
                SettingsClass.sendToMeosEnabled = False
            else:
                SettingsClass.sendToMeosEnabled = (sett.Value == "True")
        return SettingsClass.sendToMeosEnabled

    @staticmethod
    def GetSendToMeosIP():
        if SettingsClass.sendToMeosIP is None:
            sett = DatabaseHelper.get_setting_by_key('SendToMeosIP')
            if sett is None:
                SettingsClass.sendToMeosIP = None
            else:
                SettingsClass.sendToMeosIP = sett.Value
        return SettingsClass.sendToMeosIP



    @staticmethod
    def GetSendToMeosIPPort():
        if SettingsClass.sendToMeosIPPort is None:
            sett = DatabaseHelper.get_setting_by_key('SendToMeosIPPort')
            if sett is None:
                SettingsClass.sendToMeosIPPort = 5000
            else:
                 try:
                     SettingsClass.sendToMeosIPPort = int(sett.Value)
                 except ValueError:
                     SettingsClass.sendToMeosIPPort = 5000
        return SettingsClass.sendToMeosIPPort

    @staticmethod
    def GetPowerCycle():
        if SettingsClass.powerCycle is None:
            sett = DatabaseHelper.get_setting_by_key('PowerCycle')
            if sett is None:
                SettingsClass.IncrementPowerCycle()
                SettingsClass.powerCycle = 1
            else:
                SettingsClass.powerCycle = int(sett.Value)
        return SettingsClass.powerCycle

    @staticmethod
    def IncrementPowerCycle():
        sett = DatabaseHelper.get_setting_by_key('PowerCycle')
        if sett is None:
            sett = SettingData()
            sett.Key = 'PowerCycle'
            sett.Value = '0'
        pc = int(sett.Value) + 1
        sett.Value = str(pc)
        DatabaseHelper.save_setting(sett)
