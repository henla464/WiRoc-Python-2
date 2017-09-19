__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData
import time
import math
import random

class SettingsClass(object):
    RadioIntervalLengthMicroSeconds = [4000000, 4000000, 4000000, 4000000, 4000000, 4000000]
    timeOfLastMessageAdded = time.monotonic()
    statusMessageBaseInterval = None
    loraAckMessageWaitTimeout = None
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
    sendToBlenoEnabled = None
    wiRocDeviceName = None
    forceReconfigure = False

    connectedComputerIsWiRocDevice = False
    timeConnectedComputerIsWiRocDeviceChanged = None
    siStationNumber = 0
    timeSIStationNumberChanged = None

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
        if settingsName == 'StatusMessageBaseInterval':
            SettingsClass.statusMessageBaseInterval = None
        if settingsName == 'LoraAckMessageWaitTimeout':
            SettingsClass.loraAckMessageWaitTimeout = None
        if settingsName == 'SendToBlenoEnabled':
            SettingsClass.sendToBlenoEnabled = None
        if settingsName == 'WiRocDeviceName':
            SettingsClass.wiRocDeviceName = None
        if settingsName == 'WiRocDeviceName':
            SettingsClass.wiRocDeviceName = None

        if markDirtyInDatabase:
            SettingsClass.SetSetting("ConfigDirty", "1")
            SettingsClass.SetSetting("WebConfigDirty", "1")

    @staticmethod
    def IsDirty(settingsName, checkSettingForDirty = True, mainConfigDirty = True):
        isDirty = "0"
        if checkSettingForDirty:
            if mainConfigDirty:
                isDirty = SettingsClass.GetSetting("ConfigDirty")
            else:
                isDirty = SettingsClass.GetSetting("WebConfigDirty")
        if isDirty is not None and isDirty == "1":
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
            SettingsClass.statusMessageBaseInterval = None
            SettingsClass.loraAckMessageWaitTimeout = None
            SettingsClass.sendStatusMessages = None
            SettingsClass.sendToBlenoEnabled = None
            SettingsClass.wiRocDeviceName = None
            if mainConfigDirty:
                SettingsClass.SetSetting("ConfigDirty", "0")
            else:
                SettingsClass.SetSetting("WebConfigDirty", "0")
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
            if settingsName == 'StatusMessageBaseInterval':
                return SettingsClass.statusMessageBaseInterval is None
            if settingsName == 'LoraAckMessageWaitTimeout':
                return SettingsClass.loraAckMessageWaitTimeout is None
            if settingsName == 'SendStatusMessages':
                return SettingsClass.sendStatusMessages is None
            if settingsName == 'SendToBlenoEnabled':
                return SettingsClass.sendToBlenoEnabled is None
            if settingsName == 'WiRocDeviceName':
                return SettingsClass.wiRocDeviceName is None

        return True

    @staticmethod
    def SetSetting(key, value):
        sd = DatabaseHelper.get_setting_by_key(key)
        if sd is None:
            sd = SettingData()
            sd.Key = key
        sd.Value = value
        sd = DatabaseHelper.save_setting(sd)
        SettingsClass.SetConfigurationDirty(key)
        return sd

    @staticmethod
    def GetSetting(key):
        sd = DatabaseHelper.get_setting_by_key(key)
        if sd is None:
            return None
        return sd.Value

    @staticmethod
    def GetChannel(mainConfigDirty = True):
        if SettingsClass.IsDirty("Channel", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('Channel')
            if sett is None:
                SettingsClass.channel = 1
            else:
                SettingsClass.channel = int(sett.Value)
        return SettingsClass.channel

    @staticmethod
    def GetDataRate(mainConfigDirty = True):
        if SettingsClass.IsDirty("DataRate", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('DataRate')
            if sett is None:
                SettingsClass.dataRate = 293
            else:
                SettingsClass.dataRate = int(sett.Value)
        return SettingsClass.dataRate

    @staticmethod
    def GetAcknowledgementRequested(mainConfigDirty = True):
        if SettingsClass.IsDirty("AcknowledgementRequested", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
            if sett is None:
                SettingsClass.acknowledgementRequested = True
            else:
                SettingsClass.acknowledgementRequested = (sett.Value == "1")
        return SettingsClass.acknowledgementRequested

    @staticmethod
    def GetSendToMeosEnabled(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendToMeosEnabled", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendToMeosEnabled')
            if sett is None:
                SettingsClass.sendToMeosEnabled = False
            else:
                SettingsClass.sendToMeosEnabled = (sett.Value == "1")
        return SettingsClass.sendToMeosEnabled

    @staticmethod
    def GetSendToMeosIP(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendToMeosIP", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendToMeosIP')
            if sett is None:
                SettingsClass.sendToMeosIP = None
            else:
                SettingsClass.sendToMeosIP = sett.Value
        return SettingsClass.sendToMeosIP



    @staticmethod
    def GetSendToMeosIPPort(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendToMeosIPPort", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendToMeosIPPort')
            if sett is None:
                SettingsClass.sendToMeosIPPort = 10000
            else:
                 try:
                     SettingsClass.sendToMeosIPPort = int(sett.Value)
                 except ValueError:
                     SettingsClass.sendToMeosIPPort = 10000
        return SettingsClass.sendToMeosIPPort

    @staticmethod
    def GetSendToBlenoEnabled(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendToBlenoEnabled", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendToBlenoEnabled')
            if sett is None:
                SettingsClass.sendToBlenoEnabled = False
            else:
                SettingsClass.sendToBlenoEnabled = (sett.Value == "1")
        return SettingsClass.sendToBlenoEnabled

    @staticmethod
    def GetPowerCycle(mainConfigDirty = True):
        if SettingsClass.IsDirty("PowerCycle", True, mainConfigDirty):
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

    @staticmethod
    def GetReceiveSIAdapterActive(mainConfigDirty = True):
        if SettingsClass.IsDirty("ReceiveSIAdapterActive", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('ReceiveSIAdapterActive')
            if sett is None:
                SettingsClass.receiveSIAdapterActive = False
            else:
                SettingsClass.receiveSIAdapterActive = (sett.Value == "1")
        return SettingsClass.receiveSIAdapterActive

    @staticmethod
    def SetReceiveSIAdapterActive(val):
        if val == SettingsClass.receiveSIAdapterActive:
            return None

        sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', val)
        SettingsClass.receiveSIAdapterActive = (sett.Value == "1")


    @staticmethod
    def GetSendSerialAdapterActive(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendSerialAdapterActive", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
            if sett is None:
                SettingsClass.SetSendSerialAdapterActive("0")
                SettingsClass.sendSerialAdapterActive = False
            else:
                SettingsClass.sendSerialAdapterActive = (sett.Value == "1")
        return SettingsClass.sendSerialAdapterActive

    @staticmethod
    def SetSendSerialAdapterActive(val):
        if val == SettingsClass.sendSerialAdapterActive:
            return None

        sett = SettingsClass.SetSetting('SendSerialAdapterActive', val)
        SettingsClass.sendSerialAdapterActive = (sett.Value == "1")

    @staticmethod
    def GetLoraMode():
        if SettingsClass.GetSendSerialAdapterActive(): #and output = SERIAL
            # connected to computer or other WiRoc
            return "RECEIVE"
        elif SettingsClass.GetSendToMeosEnabled(): #and output = MEOS
            # configured to send to Meos over network/wifi
            return "RECEIVE"
        else:
            return "SEND"

    channelData = None
    microSecondsToSendAMessage = None
    microSecondsToSendAnAckMessage = None
    @staticmethod
    def GetRetryDelay(retryNumber, mainConfigDirty = True):
        if SettingsClass.IsDirty("Channel", True, mainConfigDirty) \
                or SettingsClass.channelData is None \
                or SettingsClass.microSecondsToSendAMessage is None:
            dataRate = SettingsClass.GetDataRate()
            channel = SettingsClass.GetChannel()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
            messageLengthInBytes = 24 # typical length
            SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)
        microSecondsDelay = SettingsClass.microSecondsToSendAMessage * 2.5 * math.pow(1.3, retryNumber) + random.uniform(0, 1)*SettingsClass.microSecondsToSendAMessage
        return microSecondsDelay

    @staticmethod
    def GetMaxRetries():
        return 5

    @staticmethod
    def GetSendStatusMessages(mainConfigDirty = True):
        if SettingsClass.IsDirty("SendStatusMessages", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('SendStatusMessages')
            if sett is None:
                SettingsClass.sendStatusMessages = True
            else:
                SettingsClass.sendStatusMessages = (sett.Value == "1")
        return SettingsClass.sendStatusMessages

    @staticmethod
    def SetTimeOfLastMessageAdded():
        SettingsClass.timeOfLastMessageAdded = time.monotonic()

    @staticmethod
    def GetTimeOfLastMessageAdded():
        return SettingsClass.timeOfLastMessageAdded

    @staticmethod
    def SetForceReconfigure(val):
        SettingsClass.forceReconfigure = val

    @staticmethod
    def GetForceReconfigure():
        return SettingsClass.forceReconfigure

    currentTime = time.monotonic()

    @staticmethod
    def GetLoraAckMessageWaitTimeoutS():
        if SettingsClass.microSecondsToSendAMessage is None:
            dataRate = SettingsClass.GetDataRate()
            channel = SettingsClass.GetChannel()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
            messageLengthInBytes = 24  # typical length
            SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)

        return 1+(SettingsClass.microSecondsToSendAMessage * 2.1)/1000000

    @staticmethod
    def GetLoraAckMessageSendingTimeS():
        if SettingsClass.microSecondsToSendAnAckMessage is None:
            dataRate = SettingsClass.GetDataRate()
            channel = SettingsClass.GetChannel()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
            messageLengthInBytes = 6  # typical length
            SettingsClass.microSecondsToSendAnAckMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)

        return 0.2+(SettingsClass.microSecondsToSendAnAckMessage)/1000000

    relayPathNo = 0
    @staticmethod
    def UpdateRelayPathNumber(sequenceNo):
        if sequenceNo > SettingsClass.relayPathNo:
            SettingsClass.relayPathNo = sequenceNo

    @staticmethod
    def GetRelayPathNumber():
        return SettingsClass.relayPathNo

    @staticmethod
    def GetStatusMessageInterval():
        if SettingsClass.statusMessageBaseInterval is None: #skip isDirty call, check directly
            sett = DatabaseHelper.get_setting_by_key('StatusMessageBaseInterval')
            if sett is None:
                SettingsClass.SetSetting('StatusMessageBaseInterval', 60)
                SettingsClass.statusMessageBaseInterval = 60
            else:
                try:
                    SettingsClass.statusMessageBaseInterval = int(sett.Value)
                except ValueError:
                    SettingsClass.statusMessageBaseInterval = 60
        return SettingsClass.statusMessageBaseInterval + (7*SettingsClass.GetRelayPathNumber()) + random.randint(0, 9)

    @staticmethod
    def GetWiRocDeviceName(mainConfigDirty = True):
        if SettingsClass.IsDirty("WiRocDeviceName", True, mainConfigDirty):
            sett = DatabaseHelper.get_setting_by_key('WiRocDeviceName')
            if sett is None:
                SettingsClass.wiRocDeviceName = None
            else:
                SettingsClass.wiRocDeviceName = sett.Value
        return SettingsClass.wiRocDeviceName

    @staticmethod
    def GetReconfigureInterval():
        return 10

    @staticmethod
    def SetConnectedComputerIsWiRocDevice():
        SettingsClass.connectedComputerIsWiRocDevice = True
        SettingsClass.timeConnectedComputerIsWiRocDeviceChanged = time.monotonic()

    @staticmethod
    def GetConnectedComputerIsWiRocDevice():
        return SettingsClass.connectedComputerIsWiRocDevice

    @staticmethod
    def Tick():
        if SettingsClass.timeConnectedComputerIsWiRocDeviceChanged is not None and \
                           time.monotonic() > SettingsClass.timeConnectedComputerIsWiRocDeviceChanged + 6 * SettingsClass.GetReconfigureInterval():
            SettingsClass.timeConnectedComputerIsWiRocDeviceChanged = None
            SettingsClass.connectedComputerIsWiRocDevice = False
        if SettingsClass.timeSIStationNumberChanged is not None and \
                        time.monotonic() > SettingsClass.timeSIStationNumberChanged + 6 * SettingsClass.GetReconfigureInterval():
            SettingsClass.timeSIStationNumberChanged = None
            SettingsClass.siStationNumber = 0

    @staticmethod
    def SetSIStationNumber(stationNumber):
        # Is refreshed from receiveSIadapter
        if stationNumber >= SettingsClass.siStationNumber:
            SettingsClass.timeSIStationNumberChanged = time.monotonic()
            SettingsClass.siStationNumber = stationNumber

    @staticmethod
    def GetSIStationNumber():
        return SettingsClass.siStationNumber