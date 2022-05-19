__author__ = 'henla464'

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import SettingData
import time
import math
import random
import os
import socket
import yaml
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
    messageIDOfLastLoraMessageSent = None

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
        return False

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
    def SetMessageIDOfLastLoraMessageSent(messageID):
        SettingsClass.messageIDOfLastLoraMessageSent = messageID

    @staticmethod
    def GetMessageIDOfLastLoraMessageSent():
        return SettingsClass.messageIDOfLastLoraMessageSent

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
    def GetLoraModule():
        if socket.gethostname() == 'chip':
            return 'RF1276T'
        else:
            return 'DRF1268DS'

    relayPathNo = 0

    @staticmethod
    def UpdateRelayPathNumber(sequenceNo):
        if sequenceNo > SettingsClass.relayPathNo:
            SettingsClass.relayPathNo = sequenceNo

    @staticmethod
    def GetRelayPathNumber():
        return SettingsClass.relayPathNo

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

        if val:
            sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', "1")
        else:
            sett = SettingsClass.SetSetting('ReceiveSIAdapterActive', "0")
        SettingsClass.receiveSIAdapterActive = (sett.Value == "1")
        cacheUntilChangedByProcess.clear()
        cache.clear()  # GetWiRocMode uses this value so needs to be invalidated

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
        cache.clear()  # GetWiRocMode uses this value so needs to be invalidated

    @staticmethod
    def SetReDCoSCombinationThreshold(val):
        sett = SettingsClass.SetSetting('ReDCoSCombinationThreshold', val)
        cacheUntilChangedByProcess.clear()
        cache.clear()


    #####
    # Changed both locally and via web services
    #####

    #####
    # DB settings changed via web services only
    #####
    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetReDCoSCombinationThreshold'), lock=rlock)
    def GetReDCoSCombinationThreshold():
        sett = DatabaseHelper.get_setting_by_key('ReDCoSCombinationThreshold')
        if sett is None:
            SettingsClass.SetSetting("ReDCoSCombinationThreshold", "5000")
            return 5000
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetShouldAlwaysRequestRepeater'), lock=rlock)
    def GetShouldAlwaysRequestRepeater():
        sett = DatabaseHelper.get_setting_by_key('ShouldAlwaysRequestRepeater')
        if sett is None:
            SettingsClass.SetSetting("ShouldAlwaysRequestRepeater", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSimulatedMessageDropPercentageRepeaterNotRequested'), lock=rlock)
    def GetSimulatedMessageDropPercentageRepeaterNotRequested():
        sett = DatabaseHelper.get_setting_by_key('SimulatedMessageDropPercentageRepeaterNotRequested')
        if sett is None:
            SettingsClass.SetSetting("SimulatedMessageDropPercentageRepeaterNotRequested", "0")
            return 0
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSimulatedMessageDropPercentageRepeaterRequested'), lock=rlock)
    def GetSimulatedMessageDropPercentageRepeaterRequested():
        sett = DatabaseHelper.get_setting_by_key('SimulatedMessageDropPercentageRepeaterRequested')
        if sett is None:
            SettingsClass.SetSetting("SimulatedMessageDropPercentageRepeaterRequested", "0")
            return 0
        return int(sett.Value)

    # Also see the code for wirocmode in the api. This is duplicated there.
    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraMode'), lock=rlock)
    def GetLoraMode():
        sett = DatabaseHelper.get_setting_by_key('LoraMode')
        if sett is None:
            SettingsClass.SetSetting("LoraMode", 'RECEIVER')
            return 'RECEIVER'
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetChannel'), lock=rlock)
    def GetChannel():
        sett = DatabaseHelper.get_setting_by_key('Channel')
        if sett is None:
            SettingsClass.SetSetting("Channel", 1)
            return 1
        return int(sett.Value)

    @staticmethod
    def GetDataRate(loraRange):
        loraDataRate = 244
        if SettingsClass.GetLoraModule() == 'RF1276T':
            if loraRange == 'L':
                loraDataRate = 293
            elif loraRange == 'ML':
                loraDataRate = 537
            elif loraRange == 'MS':
                loraDataRate = 977
            elif loraRange == 'S':
                loraDataRate = 1758
        else:
            if loraRange == 'UL':
                loraDataRate = 73
            elif loraRange == 'XL':
                loraDataRate = 134
            elif loraRange == 'L':
                loraDataRate = 244
            elif loraRange == 'ML':
                loraDataRate = 439
            elif loraRange == 'MS':
                loraDataRate = 781
            elif loraRange == 'S':
                loraDataRate = 1367
        return loraDataRate

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraRange'), lock=rlock)
    def GetLoraRange():
        sett = DatabaseHelper.get_setting_by_key('LoraRange')
        if sett is None:
            SettingsClass.SetSetting("LoraRange", 'L')
            return 'L'
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraPower'), lock=rlock)
    def GetLoraPower():
        sett = DatabaseHelper.get_setting_by_key('LoraPower')
        if sett is None:
            SettingsClass.SetSetting("LoraPower", str(0x16))
            return 0x16
        return int(sett.Value)

    @staticmethod
    def SetLoraPower(loraPower):
        SettingsClass.SetSetting("LoraPower", str(loraPower))
        cache.clear()

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetCodeRate'), lock=rlock)
    def GetCodeRate():
        sett = DatabaseHelper.get_setting_by_key('CodeRate')
        if sett is None:
            SettingsClass.SetSetting("CodeRate", str(0x00))
            return False
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetRxGainEnabled'), lock=rlock)
    def GetRxGainEnabled():
        sett = DatabaseHelper.get_setting_by_key('RxGainEnabled')
        if sett is None:
            SettingsClass.SetSetting("RxGainEnabled", "1")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetAcknowledgementRequested'), lock=rlock)
    def GetAcknowledgementRequested():
        sett = DatabaseHelper.get_setting_by_key('AcknowledgementRequested')
        if sett is None:
            SettingsClass.SetSetting("AcknowledgementRequested", "1")
            return True
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToSirapEnabled'), lock=rlock)
    def GetSendToSirapEnabled():
        sett = DatabaseHelper.get_setting_by_key('SendToSirapEnabled')
        if sett is None:
            SettingsClass.SetSetting("SendToSirapEnabled", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToSirapIP'), lock=rlock)
    def GetSendToSirapIP():
        sett = DatabaseHelper.get_setting_by_key('SendToSirapIP')
        if sett is None:
            return None
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToSirapIPPort'), lock=rlock)
    def GetSendToSirapIPPort():
        sett = DatabaseHelper.get_setting_by_key('SendToSirapIPPort')
        if sett is None:
            SettingsClass.SetSetting("SendToSirapIPPort", "10000")
            return 10000
        return int(sett.Value)

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerUrl'), lock=rlock)
    def GetWebServerUrl():
        sett = DatabaseHelper.get_setting_by_key('WebServerUrl')
        if sett is None:
            url = "https://monitor.wiroc.se"
            SettingsClass.SetSetting("WebServerUrl", url)
            return url
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerIP'), lock=rlock)
    def GetWebServerIP():
        try:
            host = SettingsClass.GetWebServerHost()
            import socket
            port = 443
            IPs = list(map(lambda x: x[4][0], socket.getaddrinfo('{}.'.format(host), port, type=socket.SOCK_STREAM, family=socket.AF_INET)))
            return IPs[0]
        except Exception as ex:
            return None

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerProtocol'), lock=rlock)
    def GetWebServerProtocol():
        url = SettingsClass.GetWebServerUrl()
        if url.lower().startswith('https://'):
            return 'https://'
        else:
            return 'http://'

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
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendToBlenoEnabled'), lock=rlock)
    def GetSendToBlenoEnabled():
        sett = DatabaseHelper.get_setting_by_key('SendToBlenoEnabled')
        if sett is None:
            SettingsClass.SetSetting("SendToBlenoEnabled", "0")
            return False
        return sett.Value == "1"

    channelData = None
    microSecondsToSendAMessage = None
    microSecondsToSendAnAckMessage = None

    @staticmethod
    def GetRetryDelay(retryNumber):
        loraRange = SettingsClass.GetLoraRange()
        channel = SettingsClass.GetChannel()
        loraModule = SettingsClass.GetLoraModule()
        codeRate = SettingsClass.GetCodeRate()
        SettingsClass.channelData = DatabaseHelper.get_channel(channel, loraRange, loraModule)
        messageLengthInBytes = 24  # typical length
        SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)
        # extra delay for higher error coderates
        SettingsClass.microSecondsToSendAMessage = SettingsClass.microSecondsToSendAMessage * (1+0.2*codeRate)
        microSecondsDelay = SettingsClass.microSecondsToSendAMessage * 2.5 * math.pow(1.3, retryNumber) + random.uniform(0, 2)*SettingsClass.microSecondsToSendAMessage
        return microSecondsDelay

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraAckMessageWaitTimeoutS'), lock=rlock)
    def GetLoraAckMessageWaitTimeoutS():
        if SettingsClass.microSecondsToSendAMessage is None:
            loraRange = SettingsClass.GetLoraRange()
            channel = SettingsClass.GetChannel()
            loraModule = SettingsClass.GetLoraModule()
            codeRate = SettingsClass.GetCodeRate()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, loraRange, loraModule)
            messageLengthInBytes = 24  # typical length
            SettingsClass.microSecondsToSendAMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)
            # extra delay for higher error coderates
            SettingsClass.microSecondsToSendAMessage = SettingsClass.microSecondsToSendAMessage * (1 + 0.2 * codeRate)
        return 1+(SettingsClass.microSecondsToSendAMessage * 2.1)/1000000

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraAckMessageSendingTimeS'), lock=rlock)
    def GetLoraAckMessageSendingTimeS():
        if SettingsClass.microSecondsToSendAnAckMessage is None:
            loraRange = SettingsClass.GetLoraRange()
            channel = SettingsClass.GetChannel()
            loraModule = SettingsClass.GetLoraModule()
            codeRate = SettingsClass.GetCodeRate()
            SettingsClass.channelData = DatabaseHelper.get_channel(channel, loraRange, loraModule)
            messageLengthInBytes = 10  # typical length
            SettingsClass.microSecondsToSendAnAckMessage = SettingsClass.channelData.SlopeCoefficient * (messageLengthInBytes + SettingsClass.channelData.M)
            # extra delay for higher error coderates
            SettingsClass.microSecondsToSendAnAckMessage = SettingsClass.microSecondsToSendAnAckMessage * (1 + 0.2 * codeRate)
        return 0.2+SettingsClass.microSecondsToSendAnAckMessage/1000000

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetLoraMessageTimeSendingTimeS'), lock=rlock)
    def GetLoraMessageTimeSendingTimeS(noOfBytes):
        if noOfBytes == 0:
            return 0
        loraRange = SettingsClass.GetLoraRange()
        channel = SettingsClass.GetChannel()
        loraModule = SettingsClass.GetLoraModule()
        codeRate = SettingsClass.GetCodeRate()
        SettingsClass.channelData = DatabaseHelper.get_channel(channel, loraRange, loraModule)
        microSecs = SettingsClass.channelData.SlopeCoefficient * (noOfBytes + SettingsClass.channelData.M)
        # extra delay for higher error coderates
        microSecs = microSecs * (1 + 0.2 * codeRate)
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
        f = open("../settings.yaml", "r")
        settings = yaml.load(f, Loader=yaml.BaseLoader)
        f.close()
        return settings['WiRocDeviceName']

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetWebServerHost'), lock=rlock)
    def GetWebServerHost():
        wsUrl = SettingsClass.GetWebServerUrl()
        return wsUrl.replace('http://', '').replace('https://', '')

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetSendStatusMessage'), lock=rlock)
    def GetSendStatusMessages():
        sett = DatabaseHelper.get_setting_by_key('SendStatusMessages')
        if sett is None:
            SettingsClass.SetSetting("SendStatusMessages", HardwareAbstraction.Instance.GetDefaultValueForSendStatusMessage())
            return True
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetOneWayReceiveFromSIStation'), lock=rlock)
    def GetOneWayReceiveFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('OneWayReceive')
        if sett is None:
            SettingsClass.SetSetting("OneWayReceive", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'Force4800BaudRate'), lock=rlock)
    def GetForce4800BaudRateFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('Force4800BaudRate')
        if sett is None:
            SettingsClass.SetSetting("Force4800BaudRate", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetRS232OneWayReceiveFromSIStation'), lock=rlock)
    def GetRS232OneWayReceiveFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('RS232OneWayReceive')
        if sett is None:
            SettingsClass.SetSetting("RS232OneWayReceive", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetForceRS2324800BaudRateFromSIStation'), lock=rlock)
    def GetForceRS2324800BaudRateFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('ForceRS2324800BaudRate')
        if sett is None:
            SettingsClass.SetSetting("ForceRS2324800BaudRate", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetRS232Mode'), lock=rlock)
    def GetRS232Mode():
        sett = DatabaseHelper.get_setting_by_key('RS232Mode')
        if sett is None:
            SettingsClass.SetSetting("RS232Mode", "RECEIVE")
            return "RECEIVE"
        return sett.Value

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetBTSerialOneWayReceiveFromSIStation'), lock=rlock)
    def GetBTSerialOneWayReceiveFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('BTSerialOneWayReceive')
        if sett is None:
            SettingsClass.SetSetting("BTSerialOneWayReceive", "0")
            return False
        return sett.Value == "1"

    @staticmethod
    @cached(cache, key=partial(hashkey, 'GetForceBTSerial4800BaudRateFromSIStation'), lock=rlock)
    def GetForceBTSerial4800BaudRateFromSIStation():
        sett = DatabaseHelper.get_setting_by_key('ForceBTSerial4800BaudRate')
        if sett is None:
            SettingsClass.SetSetting("ForceBTSerial4800BaudRate", "0")
            return False
        return sett.Value == "1"

    #####
    # Not changed from web services
    #####
    TheBTAddress = "NoBTAddress"
    @staticmethod
    # @cached(cacheForEver, key=partial(hashkey, 'GetBTAddress'), lock=rlock) seems sometimes NoBTAddress is returned, we dont want to cache that...
    def GetBTAddress():
        if SettingsClass.TheBTAddress == "NoBTAddress":
            hcitoolResp = os.popen("hcitool dev").read()
            hcitoolResp = hcitoolResp.replace("Devices:", "")
            hcitoolResp = hcitoolResp.strip()
            hcitoolRespWords = hcitoolResp.split()
            if len(hcitoolRespWords) > 1 and len(hcitoolRespWords[1]) == 17:
                btAddress = hcitoolRespWords[1]
                SettingsClass.TheBTAddress = btAddress
        return SettingsClass.TheBTAddress

    @staticmethod
    #@cached(cacheForEver, key=partial(hashkey, 'GetBTAddressAsInt'), lock=rlock)
    def GetBTAddressAsInt():
        btAddressAsString = SettingsClass.GetBTAddress()
        if btAddressAsString == "NoBTAddress":
            return 0
        else:
            btAddressAsString = btAddressAsString.replace(':', '')
            btAddressAsInt = int(btAddressAsString, 16)
            return btAddressAsInt

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
        return sett.Value == "1"

    @staticmethod
    @cached(cacheUntilChangedByProcess, key=partial(hashkey, 'GetSendSerialAdapterActive'), lock=rlock)
    def GetSendSerialAdapterActive():
        sett = DatabaseHelper.get_setting_by_key('SendSerialAdapterActive')
        if sett is None:
            SettingsClass.SetSetting("SendSerialAdapterActive", "0")
            return False
        return sett.Value == "1"
