__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData
from datetime import datetime

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    timeOfLastMessageAdded = datetime.now()
    statusMessageInterval = None
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
    sendStatusMessages = None

    @staticmethod
    def SetConfigurationDirty(settingsName=None, markDirtyInDatabase = False):
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
        if settingsName == 'FirstRetryDelay':
            SettingsClass.firstRetryDelay = None
        if settingsName == 'SecondRetryDelay':
            SettingsClass.secondRetryDelay = None
        if settingsName == 'StatusMessageInterval':
            SettingsClass.statusMessageInterval = None
        if settingsName == 'SendStatusMessages':
            SettingsClass.sendStatusMessages = None

        if markDirtyInDatabase:
            SettingsClass.SetSetting("ConfigDirty", True)

    @staticmethod
    def IsDirty(settingsName):
        isDirty = SettingsClass.GetSetting("ConfigDirty")
        if isDirty is not None and isDirty.lower() == "1":
            SettingsClass.channel = None
            SettingsClass.dataRate = None
            SettingsClass.acknowledgementRequested = None
            SettingsClass.sendToMeosEnabled = None
            SettingsClass.sendToMeosIP = None
            SettingsClass.sendToMeosIPPort = None
            SettingsClass.powerCycle = None
            SettingsClass.receiveSIAdapterActive = None
            SettingsClass.sendSerialAdapterActive = None
            SettingsClass.firstRetryDelay = None
            SettingsClass.secondRetryDelay = None
            SettingsClass.statusMessageInterval = None
            SettingsClass.sendStatusMessages = None
            return True
        else:
            if settingsName == 'Channel':
                return SettingsClass.channel is None
            if settingsName == 'DataRate':
                return SettingsClass.dataRate is None
            if settingsName == 'AcknowledgementRequested':
                return SettingsClass.acknowledgementRequested is None
            if settingsName == 'SendToMeosEnabled':
                return SettingsClass.sendToMeosEnabled is None
            if settingsName == 'SendToMeosIP':
                return SettingsClass.sendToMeosIP is None
            if settingsName == 'SendToMeosIPPort':
                return SettingsClass.sendToMeosIPPort is None
            if settingsName == 'PowerCycle':
                return SettingsClass.powerCycle is None
            if settingsName == 'ReceiveSIAdapterActive':
                return SettingsClass.receiveSIAdapterActive is None
            if settingsName == 'SendSerialAdapterActive':
                return SettingsClass.sendSerialAdapterActive is None
            if settingsName == 'FirstRetryDelay':
                return SettingsClass.firstRetryDelay is None
            if settingsName == 'SecondRetryDelay':
                return SettingsClass.secondRetryDelay is None
            if settingsName == 'StatusMessageInterval':
                return SettingsClass.statusMessageInterval is None
            if settingsName == 'SendStatusMessages':
                return SettingsClass.sendStatusMessages is None

        return True

    @staticmethod
    def SetSetting(key, value, web = False):
        sd = DatabaseHelper.mainDatabaseHelper.get_setting_by_key(key)
        if sd is None:
            sd = SettingData()
            sd.Key = key
        sd.Value = value
        sd = DatabaseHelper.mainDatabaseHelper.save_setting(sd)
        SettingsClass.SetConfigurationDirty(key)
        return sd

    @staticmethod
    def GetSetting(key):
        sd = DatabaseHelper.mainDatabaseHelper.get_setting_by_key(key)
        if sd is None:
            return None
        return sd.Value

    @staticmethod
    def GetChannel(web = False):
        if SettingsClass.IsDirty("Channel"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('Channel')
            if sett is None:
                SettingsClass.channel = 1
            else:
                SettingsClass.channel = int(sett.Value)
        return SettingsClass.channel

    @staticmethod
    def GetDataRate(web = False):
        if SettingsClass.IsDirty("DataRate"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('DataRate')
            if sett is None:
                SettingsClass.dataRate = 586
            else:
                SettingsClass.dataRate = int(sett.Value)
        return SettingsClass.dataRate

    @staticmethod
    def GetAcknowledgementRequested(web = False):
        if SettingsClass.IsDirty("AcknowledgementRequested"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('AcknowledgementRequested')
            if sett is None:
                SettingsClass.acknowledgementRequested = False
            else:
                SettingsClass.acknowledgementRequested = (sett.Value == "1")
        return SettingsClass.acknowledgementRequested

    @staticmethod
    def GetSendToMeosEnabled(web = False):
        if SettingsClass.IsDirty("SendToMeosEnabled"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendToMeosEnabled')
            if sett is None:
                SettingsClass.sendToMeosEnabled = False
            else:
                SettingsClass.sendToMeosEnabled = (sett.Value == "1")
        return SettingsClass.sendToMeosEnabled

    @staticmethod
    def GetSendToMeosIP(web = False):
        if SettingsClass.IsDirty("SendToMeosIP"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendToMeosIP')
            if sett is None:
                SettingsClass.sendToMeosIP = None
            else:
                SettingsClass.sendToMeosIP = sett.Value
        return SettingsClass.sendToMeosIP



    @staticmethod
    def GetSendToMeosIPPort(web = False):
        if SettingsClass.IsDirty("SendToMeosIPPort"):
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
        if SettingsClass.IsDirty("PowerCycle"):
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
        if SettingsClass.IsDirty("ReceiveSIAdapterActive"):
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
        if SettingsClass.IsDirty("SendSerialAdapterActive"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
            if sett is None:
                SettingsClass.SetSendSerialAdapterActive(False)
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
        if SettingsClass.IsDirty("FirstRetryDelay"):
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
        if SettingsClass.IsDirty("SecondRetryDelay"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SecondRetryDelay')
            if sett is None:
                SettingsClass.secondRetryDelay = 20
            else:
                try:
                    SettingsClass.secondRetryDelay = int(sett.Value)
                except ValueError:
                    SettingsClass.secondRetryDelay = 20
        return SettingsClass.secondRetryDelay

    @staticmethod
    def GetSendStatusMessages():
        if SettingsClass.IsDirty("SendStatusMessages"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('SendStatusMessages')
            if sett is None:
                SettingsClass.sendStatusMessages = True
            else:
                SettingsClass.sendStatusMessages = (sett.Value == "1")
        return SettingsClass.sendStatusMessages

    @staticmethod
    def SetTimeOfLastMessageAdded():
        SettingsClass.timeOfLastMessageAdded = datetime.now()

    @staticmethod
    def GetTimeOfLastMessageAdded():
        return SettingsClass.timeOfLastMessageAdded

    @staticmethod
    def GetStatusMessageInterval():
        if SettingsClass.IsDirty("StatusMessageInterval"):
            sett = DatabaseHelper.mainDatabaseHelper.get_setting_by_key('StatusMessageInterval')
            if sett is None:
                SettingsClass.statusMessageInterval = 10
            else:
                try:
                    SettingsClass.statusMessageInterval = int(sett.Value)
                except ValueError:
                    SettingsClass.statusMessageInterval = 10
        return SettingsClass.statusMessageInterval