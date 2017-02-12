__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    configurationDirty = False
    MessagesToSendExists = True
    channel = None
    dataRate = None
    acknowledgementRequested = None
    sendToMeosEnabled = None
    sendToMeosIP = None
    sendToMeosIPPort = None
    powerCycle = None
    receiveSIAdapterActive = None
    sendSerialAdapterActive = None
    firstRetryDelay = None
    secondRetryDelay = None

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
        if settingsName == 'ReceiveSIAdapterActive':
            SettingsClass.receiveSIAdapterActive = None
        if settingsName == 'SendSerialAdapterActive':
            SettingsClass.sendSerialAdapterActive = None

    @staticmethod
    def SetSetting(key, value, web = False):
        sd = None
        if web:
            sd = DatabaseHelper.webDatabaseHelper.get_setting_by_key(key)
        else:
            sd = DatabaseHelper.mainDatabaseHelper.get_setting_by_key(key)
        if sd is None:
            sd = SettingData()
            sd.Key = key
        sd.Value = value
        if web:
            sd = DatabaseHelper.webDatabaseHelper.save_setting(sd)
        else:
            sd = DatabaseHelper.mainDatabaseHelper.save_setting(sd)
        SettingsClass.SetConfigurationDirty(key)
        return sd

    @staticmethod
    def GetChannel(web = False):
        if SettingsClass.channel is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('Channel')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('Channel')
            if sett is None:
                SettingsClass.channel = 1
            else:
                SettingsClass.channel = int(sett.Value)
        return SettingsClass.channel

    @staticmethod
    def GetDataRate(web = False):
        if SettingsClass.dataRate is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('DataRate')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('DataRate')
            if sett is None:
                SettingsClass.dataRate = 586
            else:
                SettingsClass.dataRate = int(sett.Value)
        return SettingsClass.dataRate

    @staticmethod
    def GetAcknowledgementRequested(web = False):
        if SettingsClass.acknowledgementRequested is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('AcknowledgementRequested')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('AcknowledgementRequested')
            if sett is None:
                SettingsClass.acknowledgementRequested = False
            else:
                SettingsClass.acknowledgementRequested = (sett.Value.lower() == "true")
        return SettingsClass.acknowledgementRequested

    @staticmethod
    def GetSendToMeosEnabled(web = False):
        if SettingsClass.sendToMeosEnabled is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosEnabled')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendToMeosEnabled')
            if sett is None:
                SettingsClass.sendToMeosEnabled = False
            else:
                SettingsClass.sendToMeosEnabled = (sett.Value == "True")
        return SettingsClass.sendToMeosEnabled

    @staticmethod
    def GetSendToMeosIP(web = False):
        if SettingsClass.sendToMeosIP is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosIP')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendToMeosIP')
            if sett is None:
                SettingsClass.sendToMeosIP = None
            else:
                SettingsClass.sendToMeosIP = sett.Value
        return SettingsClass.sendToMeosIP



    @staticmethod
    def GetSendToMeosIPPort(web = False):
        if SettingsClass.sendToMeosIPPort is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendToMeosIPPort')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendToMeosIPPort')
            if sett is None:
                SettingsClass.sendToMeosIPPort = 5000
            else:
                 try:
                     SettingsClass.sendToMeosIPPort = int(sett.Value)
                 except ValueError:
                     SettingsClass.sendToMeosIPPort = 5000
        return SettingsClass.sendToMeosIPPort

    @staticmethod
    def GetPowerCycle(web = False):
        if SettingsClass.powerCycle is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('PowerCycle')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('PowerCycle')
            if sett is None:
                SettingsClass.IncrementPowerCycle()
                SettingsClass.powerCycle = 1
            else:
                SettingsClass.powerCycle = int(sett.Value)
        return SettingsClass.powerCycle

    @staticmethod
    def IncrementPowerCycle():
        sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('PowerCycle')
        if sett is None:
            sett = SettingData()
            sett.Key = 'PowerCycle'
            sett.Value = '0'
        pc = int(sett.Value) + 1
        sett.Value = str(pc)
        DatabaseHelper.mainDatabaseHelper.save_setting(sett)

    @staticmethod
    def GetReceiveSIAdapterActive(web = False):
        if SettingsClass.receiveSIAdapterActive is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('ReceiveSIAdapterActive')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('ReceiveSIAdapterActive')
            if sett is None:
                SettingsClass.receiveSIAdapterActive = False
            else:
                SettingsClass.receiveSIAdapterActive = (sett.Value == "1")
        return SettingsClass.receiveSIAdapterActive

    @staticmethod
    def SetReceiveSIAdapterActive(val, web = False):
        if val == SettingsClass.receiveSIAdapterActive:
            return None

        sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', val, web)
        SettingsClass.receiveSIAdapterActive = (sett.Value == "1")


    @staticmethod
    def GetSendSerialAdapterActive(web = False):
        if SettingsClass.sendSerialAdapterActive is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
            if sett is None:
                SettingsClass.sendSerialAdapterActive = False
            else:
                SettingsClass.sendSerialAdapterActive = (sett.Value == "1")
        return SettingsClass.sendSerialAdapterActive

    @staticmethod
    def SetSendSerialAdapterActive(val, web = False):
        if val == SettingsClass.sendSerialAdapterActive:
            return None

        sett = SettingsClass.SetSetting('SendSerialAdapterActive', val, web)
        SettingsClass.sendSerialAdapterActive = (sett.Value == "1")

    @staticmethod
    def GetLoraMode():
        if SettingsClass.GetSendSerialAdapterActive(): #and output = SERIAL
            # connected to computer or other WiRoc
            return "RECEIVE"
        elif SettingsClass.GetSendToMeosEnabled(): #and output = MEOS
            # configured to send to Meos over network/wifi
            return "RECEIVE"
        elif False: # todo: bluetooth out enabled
            return "RECEIVE"
        else:
            return "SEND"

    @staticmethod
    def SetMessagesToSendExists(val = True):
        SettingsClass.MessagesToSendExists = val

    @staticmethod
    def GetMessagesToSendExists():
        return SettingsClass.MessagesToSendExists

    @staticmethod
    def GetFirstRetryDelay(web=False):
        if SettingsClass.firstRetryDelay is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('FirstRetryDelay')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('FirstRetryDelay')
            if sett is None:
                SettingsClass.firstRetryDelay = 20
            else:
                try:
                    SettingsClass.firstRetryDelay = int(sett.Value)
                except ValueError:
                    SettingsClass.firstRetryDelay = 20
        return SettingsClass.firstRetryDelay

    @staticmethod
    def GetSecondRetryDelay(web=False):
        if SettingsClass.secondRetryDelay is None:
            sett = None
            if web:
                sett = DatabaseHelper.webDatabaseHelper.get_setting_by_key('SecondRetryDelay')
            else:
                sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SecondRetryDelay')
            if sett is None:
                SettingsClass.secondRetryDelay = 20
            else:
                try:
                    SettingsClass.secondRetryDelay = int(sett.Value)
                except ValueError:
                    SettingsClass.secondRetryDelay = 20
        return SettingsClass.secondRetryDelay
