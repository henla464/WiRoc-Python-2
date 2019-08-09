__author__ = 'henla464'

from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData
import time
import math
import random
import os
from cachetools import cached, TTLCache
from cachetools.keys import hashkey
from functools import partial
from threading import RLock


cache = TTLCache(maxsize=100, ttl=300)  # 300 seconds
cacheForEver = TTLCache(maxsize=100, ttl=30000)  # 30000 seconds (500 min)
cacheUntilChangedByProcess = TTLCache(maxsize=100, ttl=30000)  # 30000 seconds (500 min)
rlock = RLock()

class SettingsClass(object):
    timeOfLastMessageAdded = time.monotonic()
    timeOfLastMessageSentToLora = time.monotonic()
    receiveSIAdapterActive = None
    sendSerialAdapterActive = None
    forceReconfigure = False
    webServerIP = None
    connectedComputerIsWiRocDevice = False
    timeConnectedComputerIsWiRocDeviceChanged = None
    siStationNumber = 0
    timeSIStationNumberChanged = None
    hasReceivedMessageFromRepeater = False
    batteryIsLowReceived = False
    deviceId = None

    #####
    # Static/class settings
    #####
    @staticmethod
    def SetHasReceivedMessageFromRepeater():
        SettingsClass.hasReceivedMessageFromRepeater = True

    @staticmethod
    def GetHasReceivedMessageFromRepeater():
        return SettingsClass.hasReceivedMessageFromRepeater

    @staticmethod
    def GetStatusAcknowledgementRequested():
        return True

    @staticmethod
    def GetMaxRetries():
        return 5

    @staticmethod
    def SetTimeOfLastMessageSentToLora():
        SettingsClass.timeOfLastMessageSentToLora = time.monotonic()

    @staticmethod
    def GetTimeOfLastMessageSentToLora():
        return SettingsClass.timeOfLastMessageSentToLora

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
                        time.monotonic() > SettingsClass.timeConnectedComputerIsWiRocDeviceChanged + 60:
            SettingsClass.timeConnectedComputerIsWiRocDeviceChanged = None
            SettingsClass.connectedComputerIsWiRocDevice = False

        # Clear cache if settings has been updated from webservices
        sett = DatabaseHelper.get_setting_by_key('SettingUpdatedByWebService')
        if sett is None:
            return
        if sett.Value == "1":
            SettingsClass.ClearSettingUpdatedByWebService()
            cache.clear()

    @staticmethod
    def SetSIStationNumber(stationNumber):
        # Is refreshed from receiveSIadapter, if several stations connected then set the
        # highest station number. Set a the lower station number if a higher hasn't been
        # set for a long time.
        if stationNumber >= SettingsClass.siStationNumber or \
                (
                    time.monotonic() > SettingsClass.timeSIStationNumberChanged + 600):
            SettingsClass.timeSIStationNumberChanged = time.monotonic()
            SettingsClass.siStationNumber = stationNumber

    @staticmethod
    def GetSIStationNumber():
        return SettingsClass.siStationNumber

    @staticmethod
    def SetBatteryIsLowReceived(batteryIsLowReceived):
        SettingsClass.batteryIsLowReceived = batteryIsLowReceived

    @staticmethod
    def GetBatteryIsLowReceived():
        return SettingsClass.batteryIsLowReceived

    @staticmethod
    def SetDeviceId(deviceId):
        SettingsClass.deviceId = deviceId

    @staticmethod
    def GetDeviceId():
        return SettingsClass.deviceId

    @staticmethod
    def GetWebServerIP():
        return SettingsClass.webServerIP

    @staticmethod
    def SetWebServerIP(ip):
        SettingsClass.webServerIP = ip

    relayPathNo = 0
    @staticmethod
    def UpdateRelayPathNumber(sequenceNo):
        if sequenceNo > SettingsClass.relayPathNo:
            SettingsClass.relayPathNo = sequenceNo

    @staticmethod
    def GetRelayPathNumber():
        return SettingsClass.relayPathNo

    @staticmethod
    def GetWebServerIPUrlBackground(webServerUrl):
        ip = SettingsClass.GetWebServerIP()
        if ip == None:
            return None
        host = webServerUrl.replace('http://', '').replace('https://', '')
        IPUrl = webServerUrl.replace(host, ip)
        return IPUrl

    @staticmethod
    def GetWebServerHostBackground(wsUrl):
        return wsUrl.replace('http://', '').replace('https://', '')

    #####
    # Set DB values
    #####
    @staticmethod
    def SetSettingUpdatedByWebService():
        SettingsClass.SetSetting("SettingUpdatedByWebService", "1")

    @staticmethod
    def ClearSettingUpdatedByWebService():
        SettingsClass.SetSetting("SettingUpdatedByWebService", "0")

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
    def SetReceiveSIAdapterActive(val):
        if val == SettingsClass.receiveSIAdapterActive:
            return None

        if val == True:
            sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', "1")
        else:
            sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', "0")
        SettingsClass.receiveSIAdapterActive = (sett.Value == "1")
        cacheUntilChangedByProcess.clear()
        cache.clear()  #GetWiRocMode uses this value so needs to be invalidated

    @staticmethod
    def SetSetting(key, value):
        sd = DatabaseHelper.get_setting_by_key(key)
        if sd is None:
            sd = SettingData()
            sd.Key = key
        sd.Value = value
        sd = DatabaseHelper.save_setting(sd)
        return sd

    @staticmethod
    def SetSendSerialAdapterActive(val):
        if val == SettingsClass.sendSerialAdapterActive:
            return None

        sett = SettingsClass.SetSetting('SendSerialAdapterActive', val)
        SettingsClass.sendSerialAdapterActive = (sett.Value == "1")
        cacheUntilChangedByProcess.clear()
        cache.clear() #GetWiRocMode uses this value so needs to be invalidated

     #####
     # Changed both locally and via web services
     #####
    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWiRocMode'), lock=rlock)
    def GetWiRocMode():
        if SettingsClass.GetSendSerialAdapterActive():  # and output = SERIAL
            # connected to computer or other WiRoc
            return "RECEIVER"
        elif SettingsClass.GetSendToMeosEnabled():  # and output = MEOS
            # configured to send to Meos over network/wifi
            return "RECEIVER"
        elif SettingsClass.GetReceiveSIAdapterActive():
            return "SENDER"
        else:
            return "REPEATER"

    #####
    # DB settings changed via web services only
    #####

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetChannel'), lock=rlock)
    def GetChannel():
        sett = DatabaseHelper.get_setting_by_key('Channel')
        if sett is None:
            SettingsClass.SetSetting("Channel", 1)
            return 1
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetDataRate'), lock=rlock)
    def GetDataRate():
        sett = DatabaseHelper.get_setting_by_key('DataRate')
        if sett is None:
            SettingsClass.SetSetting("DataRate", "293")
            return 293
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraPower'), lock=rlock)
    def GetLoraPower():
        sett = DatabaseHelper.get_setting_by_key('LoraPower')
        if sett is None:
            SettingsClass.SetSetting("LoraPower", str(0x07))
            return 0x07
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetAcknowledgementRequested'), lock=rlock)
    def GetAcknowledgementRequested():
        sett = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
        if sett is None:
            SettingsClass.SetSetting("AcknowledgementRequested", "1")
            return True
        return  (sett.Value == "1")

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToMeosEnabled'), lock=rlock)
    def GetSendToMeosEnabled():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosEnabled')
        if sett is None:
            SettingsClass.SetSetting("SendToMeosEnabled", "0")
            return False
        return (sett.Value == "1")

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToMeosIP'), lock=rlock)
    def GetSendToMeosIP():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosIP')
        if sett is None:
            return None
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToMeosIPPort'), lock=rlock)
    def GetSendToMeosIPPort():
        sett = DatabaseHelper.get_setting_by_key('SendToMeosIPPort')
        if sett is None:
            SettingsClass.SetSetting("SendToMeosIPPort", "10000")
            return 10000
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerUrl'), lock=rlock)
    def GetWebServerUrl():
        sett = DatabaseHelper.get_setting_by_key('WebServerUrl')
        if sett is None:
            url = "http://monitor.wiroc.se"
            SettingsClass.SetSetting("WebServerUrl", url)
            return url
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoggingServerHost'), lock=rlock)
    def GetLoggingServerHost():
        sett = DatabaseHelper.get_setting_by_key('LoggingServerHost')
        if sett is None:
            SettingsClass.SetSetting("LoggingServerHost", "")
            return ""
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoggingServerPort'), lock=rlock)
    def GetLoggingServerPort():
        sett = DatabaseHelper.get_setting_by_key('LoggingServerPort')
        if sett is None:
            SettingsClass.SetSetting("LoggingServerPort", "3000")
            return "3000"
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLogToServer'), lock=rlock)
    def GetLogToServer():
        sett = DatabaseHelper.get_setting_by_key('LogToServer')
        if sett is None:
            SettingsClass.SetSetting("LogToServer", "0")
            return False
        return (sett.Value == "1")

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToBlenoEnabled'), lock=rlock)
    def GetSendToBlenoEnabled():
        sett = DatabaseHelper.get_setting_by_key('SendToBlenoEnabled')
        if sett is None:
            SettingsClass.SetSetting("SendToBlenoEnabled", "0")
            return False
        return (sett.Value == "1")

    channelData = None
    microSecondsToSendAMessage = None
    microSecondsToSendAnAckMessage = None
    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetRetryDelay'), lock=rlock)
    def GetRetryDelay(retryNumber, mainConfigDirty = True):
        dataRate = SettingsClass.GetDataRate()
        channel = SettingsClass.GetChannel()
        SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
        messageLengthInBytes = 24 # typical length
        SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)
        microSecondsDelay = SettingsClass.microSecondsToSendAMessage * 2.5 * math.pow(1.3, retryNumber) + random.uniform(0, 1)*SettingsClass.microSecondsToSendAMessage
        return microSecondsDelay

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraAckMessageWaitTimeoutS'), lock=rlock)
    def GetLoraAckMessageWaitTimeoutS():
        if SettingsClass.microSecondsToSendAMessage is None:
            dataRate = SettingsClass.GetDataRate()
            channel = SettingsClass.GetChannel()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
            messageLengthInBytes = 24  # typical length
            SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)

        return 1+(SettingsClass.microSecondsToSendAMessage * 2.1)/1000000


    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraAckMessageSendingTimeS'), lock=rlock)
    def GetLoraAckMessageSendingTimeS():
        if SettingsClass.microSecondsToSendAnAckMessage is None:
            dataRate = SettingsClass.GetDataRate()
            channel = SettingsClass.GetChannel()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
            messageLengthInBytes = 10  # typical length
            SettingsClass.microSecondsToSendAnAckMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)

        return 0.2+(SettingsClass.microSecondsToSendAnAckMessage)/1000000

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraMessageTimeSendingTimeS'), lock=rlock)
    def GetLoraMessageTimeSendingTimeS(noOfBytes):
        if noOfBytes == 0:
            return 0
        dataRate = SettingsClass.GetDataRate()
        channel = SettingsClass.GetChannel()
        SettingsClass.channelData = DatabaseHelper.get_channel(channel, dataRate)
        microSecs = SettingsClass.channelData.SlopeCoefficient * (noOfBytes + SettingsClass.channelData.M)
        return microSecs/1000000

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetStatusMessageInterval'), lock=rlock)
    def GetStatusMessageInterval():
        sett = DatabaseHelper.get_setting_by_key('StatusMessageBaseInterval')
        if sett is None:
            SettingsClass.SetSetting('StatusMessageBaseInterval', 300)
            statusMessageBaseInterval = 300
        else:
            try:
                statusMessageBaseInterval = int(sett.Value)
            except ValueError:
                statusMessageBaseInterval = 300

        return statusMessageBaseInterval + (7 * SettingsClass.GetRelayPathNumber()) + random.randint(0, 9)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWiRocDeviceName'), lock=rlock)
    def GetWiRocDeviceName():
        sett = DatabaseHelper.get_setting_by_key('WiRocDeviceName')
        if sett is None:
            SettingsClass.SetSetting("WiRocDeviceName", None)
            return None
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerHost'), lock=rlock)
    def GetWebServerHost():
        wsUrl = SettingsClass.GetWebServerUrl()
        return wsUrl.replace('http://', '').replace('https://', '')

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerIPUrl'), lock=rlock)
    def GetWebServerIPUrl():
        ip = SettingsClass.GetWebServerIP()
        if ip == None:
            return None
        webServerUrl = SettingsClass.GetWebServerUrl()
        host = webServerUrl.replace('http://', '').replace('https://', '')
        IPUrl = webServerUrl.replace(host, ip)
        return IPUrl

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendStatusMessage'), lock=rlock)
    def GetSendStatusMessages():
        sett = DatabaseHelper.get_setting_by_key('SendStatusMessages')
        if sett is None:
            SettingsClass.SetSetting("SendStatusMessages", "1")
            return True
        return (sett.Value == "1")

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetOneWayReceiveFromSIStation'), lock=rlock)
    def GetOneWayReceiveFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
        if sett is None:
            SettingsClass.SetSetting("OneWayReceive", "0")
            return False
        return (sett.Value == "1")

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendStatusMessage'), lock=rlock)
    def GetForce4800BaudRateFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
        if sett is None:
            SettingsClass.SetSetting("Force4800BaudRate", "0")
            return False
        return (sett.Value == "1")

    #####
    # Not changed from web services
    #####

    @staticmethod
    @cached(cacheForEver, key=partial(hashkey, 'GetBTAddress'), lock=rlock)
    def GetBTAddress():
        hcitoolResp = os.popen("hcitool dev").read()
        hcitoolResp = hcitoolResp.replace("Devices:", "")
        hcitoolResp = hcitoolResp.strip()
        hcitoolRespWords = hcitoolResp.split()
        btAddress = "NoBTAddress"
        if len(hcitoolRespWords) > 1 and len(hcitoolRespWords[1]) == 17:
            btAddress = hcitoolRespWords[1]
        return btAddress

    @staticmethod
    @cached(cacheForEver, key=partial(hashkey, 'GetAPIKey'), lock=rlock)
    def GetAPIKey():
        sett = DatabaseHelper.get_setting_by_key('APIKey')
        if sett is None:
            with open('../apikey.txt', 'r') as apikeyfile:
                apiKey = apikeyfile.read()
                apiKey = apiKey.strip()
                return apiKey
        return sett.Value

    @staticmethod
    @cached(cacheForEver, key=partial(hashkey, 'GetPowerCycle'), lock=rlock)
    def GetPowerCycle():
        sett = DatabaseHelper.get_setting_by_key('PowerCycle')
        if sett is None:
            SettingsClass.SetSetting("PowerCycle", "1")
            return 1
        return int(sett.Value)


    @staticmethod
    @cached(cacheUntilChangedByProcess, key=partial(hashkey, 'GetReceiveSIAdapterActive'), lock=rlock)
    def GetReceiveSIAdapterActive():
        sett = DatabaseHelper.get_setting_by_key('ReceiveSIAdapterActive')
        if sett is None:
            SettingsClass.SetSetting("ReceiveSIAdapterActive", "0")
            return False
        return (sett.Value == "1")

    @staticmethod
    @cached(cacheUntilChangedByProcess, key=partial(hashkey, 'GetSendSerialAdapterActive'), lock=rlock)
    def GetSendSerialAdapterActive():
        sett = DatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
        if sett is None:
            SettingsClass.SetSetting("SendSerialAdapterActive", "0")
            return False
        return (sett.Value == "1")


