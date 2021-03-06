from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import LoraRadioMessage
from battery import Battery
import logging
import requests

class SendStatusAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances():
        if len(SendStatusAdapter.Instances) == 0:
            SendStatusAdapter.Instances.append(SendStatusAdapter('status1'))
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendStatusAdapter.Instances[0].GetIsInitialized()
        subscriptionShouldBeEnabled = isInitialized
        if SendStatusAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "STATUS"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendStatusAdapter.Instances) > 0:
            isInitialized = SendStatusAdapter.Instances[0].GetIsInitialized()

            webServerIPUrl = SettingsClass.GetWebServerIPUrl()
            webServerHost = SettingsClass.GetWebServerHost()
            connectionOK = SendStatusAdapter.TestConnection(webServerIPUrl,webServerHost)
            subscriptionShouldBeEnabled = isInitialized and connectionOK
            if SendStatusAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                SendStatusAdapter.WiRocLogger.info("SendStatusAdapter::EnableDisableSubscription() subscription set enabled: " + str(subscriptionShouldBeEnabled))
                SendStatusAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                DatabaseHelper.update_subscriptions(subscriptionShouldBeEnabled, SendStatusAdapter.GetDeleteAfterSent(), SendStatusAdapter.GetTypeName())


    @staticmethod
    def EnableDisableTransforms():
        return None

    def __init__(self, instanceName):
        self.instanceName = instanceName
        self.transforms = {}
        self.sock = None
        self.isInitialized = False
        self.isDBInitialized = False

    def GetInstanceName(self):
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent():
        return True

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent():
        return False

    def GetIsInitialized(self):
        return self.isInitialized

    def ShouldBeInitialized(self):
        return not self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self):
        return self.isDBInitialized

    def SetIsDBInitialized(self, val = True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        return ["LoraStatusToStatusTransform", "StatusStatusToStatusTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName):
        return self.transforms[transformName]

    def Init(self):
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def IsReadyToSend(self):
        return True

    @staticmethod
    def TestConnection(webServerIPUrl, webServerHost):
        try:
            if webServerIPUrl == None:
                SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::TestConnection() No webserverurl available (yet)")
                return False
            URL = webServerIPUrl + "/api/v1/ping"
            r = requests.get(url=URL,timeout=1, headers={'host': webServerHost})
            data = r.json()
            logging.info(data)
            return data['code'] == 0
        except Exception as ex:
            SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::TestConnection() " + webServerIPUrl + " Host: " + webServerHost + " Exception: " + str(ex))
            return False

    @staticmethod
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1

    # messageData is a bytearray
    def SendData(self, messageData, successCB, failureCB, notSentCB, callbackQueue, settingsDictionary):
        try:
            if settingsDictionary["WebServerIPUrl"]== None:
                SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::SendData No webserveripurl")
                callbackQueue.put((failureCB,))
                return False

            btAddress = SettingsClass.GetBTAddress()
            host = settingsDictionary["WebServerHost"]
            headers = {'Authorization': settingsDictionary["ApiKey"], 'host': host}

            if SettingsClass.GetDeviceId() == None:
                URL = settingsDictionary["WebServerIPUrl"] + "/api/v1/Devices/LookupDeviceByBTAddress/" + btAddress
                resp = requests.get(url=URL,timeout=1, headers=headers)
                if resp.status_code == 404:
                    wiRocDeviceName = settingsDictionary["WiRocDeviceName"]
                    device = {"BTAddress": btAddress, "name": wiRocDeviceName}  # "description": None
                    URL = settingsDictionary["WebServerIPUrl"] + "/api/v1/Devices"
                    resp = requests.post(url=URL, json=device, timeout=1, headers=headers)
                    if resp.status_code == 200:
                        retDevice = resp.json()
                        SettingsClass.SetDeviceId(retDevice['id'])
                    else:
                        callbackQueue.put((failureCB, ))
                        return False
                else:
                    retDevice = resp.json()
                    SettingsClass.SetDeviceId(retDevice['id'])

            # subdevices
            subDeviceData = messageData[LoraRadioMessage.GetHeaderSize():]
            success = True
            def grouped(iterable, n):
                "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
                return zip(*[iter(iterable)] * n)
            #/api/v1/SubDevices
            previousPathNo = None
            groupedStatii = list(grouped(subDeviceData, 2))
            distanceToHead = groupedStatii[-1][1] & 0x07
            for byte1,byte2 in groupedStatii:
                batteryPercent = (byte1 & 0xF0) >> 4
                siStationNumber = (byte1 & 0x0F) << 5
                siStationNumber = siStationNumber | (byte2 & 0xF8) >> 3
                pathNo = byte2 & 0x07
                if previousPathNo != None:
                    distanceToHead -= (pathNo - previousPathNo)
                previousPathNo = pathNo
                subDevice = {"headBTAddress": btAddress, "distanceToHead": distanceToHead}
                URL = settingsDictionary["WebServerIPUrl"] + "/api/v1/SubDevices"
                resp = requests.put(url=URL, json=subDevice,timeout=1, headers=headers)
                if resp.status_code == 200 or resp.status_code == 303:
                    subDevice2 = resp.json()
                    #subDevice stats
                    subDeviceStatus = None
                    if pathNo >= len(groupedStatii)-1: #last status (pathNo could be higher than index so >=)
                        # this WiRoc so we can get a higher precision battery percentage
                        subDeviceStatus = {"subDeviceId": subDevice2['id'],"batteryLevel":Battery.GetBatteryPercent(),
                                           "batteryLevelPrecision":101, "siStationNumber": siStationNumber}
                    else:
                        subDeviceStatus = {"subDeviceId": subDevice2['id'], "batteryLevel": batteryPercent,
                                           "batteryLevelPrecision": 16, "siStationNumber": siStationNumber}
                    URL = settingsDictionary["WebServerIPUrl"] + "/api/v1/SubDeviceStatuses"
                    resp = requests.post(url=URL, json=subDeviceStatus,timeout=1, allow_redirects=False, headers=headers)
                    success = (resp.status_code == 200 or resp.status_code == 303)
            if success:
                callbackQueue.put((successCB,))
                return True
            else:
                callbackQueue.put((failureCB,))
                return False
        except Exception as ex:
            SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::SendData() Exception: " + str(ex))
            callbackQueue.put((failureCB, ))
            return False
