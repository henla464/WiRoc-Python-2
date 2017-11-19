from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
from datamodel.datamodel import LoraRadioMessage
import logging
import requests

class SendStatusAdapter(object):
    Instances = []
    SubscriptionsEnabled = False
    DeviceId = None

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
            connectionOK = SendStatusAdapter.TestConnection()
            subscriptionShouldBeEnabled = isInitialized and connectionOK
            if SendStatusAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                logging.info("SendStatusAdapter::EnableDisableSubscription() subscription set enabled: " + str(subscriptionShouldBeEnabled))
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
    def TestConnection():
        try:
            URL = SettingsClass.GetWebServerUrl() + "/api/v1/ping"
            r = requests.get(url=URL)
            data = r.json()
            return data['code'] == 0
        except:
            logging.error("SendStatusAdapter::TestConnection() Exception")
            return False


    # messageData is a bytearray
    def SendData(self, messageData):
        try:
            if SendStatusAdapter.DeviceId == None:
                btAddress = SettingsClass.GetBTAddress()
                URL = SettingsClass.GetWebServerUrl() + "/api/v1/Devices/LookupDeviceByBTAddress/" +  btAddress
                resp = requests.get(url=URL)
                device = resp.json()
                if device['id'] == None:
                    wiRocDeviceName = SettingsClass.GetWiRocDeviceName()
                    device = {"BTAddress": btAddress, "name": wiRocDeviceName}  # "description": None
                    URL = SettingsClass.GetWebServerUrl() + "/api/v1/Devices"
                    resp = requests.post(url=URL, json=device)
                    if resp.status_code == 200:
                        device = resp.json()
                        SendStatusAdapter.DeviceId = device['id']
                    else:
                        return False
                else:
                    SendStatusAdapter.DeviceId = device['id']

                # subdevices
                subDeviceData = messageData[LoraRadioMessage.GetHeaderSize():]

                def grouped(iterable, n):
                    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
                    return zip(*[iter(iterable)] * n)
                #/api/v1/SubDevices
                for byte1,byte2 in grouped(subDeviceData, 2):
                    batteryPercent = byte1 & 0xF0
                    siStationNumber = (byte1 & 0x0F) << 5
                    siStationNumber = siStationNumber | (byte2 & 0xF8) >> 3
                    pathNo = byte2 & 0x07
                    subDevice = {"headBTAddress": btAddress, "distanceToHead": pathNo}
                    URL = SettingsClass.GetWebServerUrl() + "/api/v1/SubDevices"
                    resp = requests.put(url=URL, json=subDevice)
                    if resp.status_code == 200:
                        subDevice2 = resp.json()
                        #subDevice stats
                        subDeviceStatus = {"subDeviceId": subDevice2.id,"batteryLevel":batteryPercent, "batteryLevelprecision":16}
                        URL = SettingsClass.GetWebServerUrl() + "/api/v1/SubDeviceStatuses"
                        resp = requests.post(url=URL, json=subDeviceStatus)
                        if resp.status_code != 200:
                            return False
                    else:
                        return False
        except:
            logging.error("SendStatusAdapter::SendData() Exception")
            return False
