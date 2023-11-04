from loraradio.LoraRadioMessageCreator import LoraRadioMessageCreator
from loraradio.LoraRadioMessageRS import LoraRadioMessageRS, LoraRadioMessageStatusRS
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
from battery import Battery
import logging
import requests
import json


class SendStatusAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances():
        if len(SendStatusAdapter.Instances) == 0:
            SendStatusAdapter.Instances.append(SendStatusAdapter('status1'))
            return True

        # check if subscription should be enabled or disabled, if so return true sot that init/enabledisablesubscription run
        isInitialized = SendStatusAdapter.Instances[0].GetIsInitialized()

        connectionOK = SendStatusAdapter.IsConnectionOK()
        subscriptionShouldBeEnabled = isInitialized and connectionOK
        if SendStatusAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "STATUS"

    @staticmethod
    def IsConnectionOK():
        connectionOK = False
        if SettingsClass.GetSendStatusMessages():
            webServerUrl = SettingsClass.GetWebServerUrl()
            connectionOK = SendStatusAdapter.TestConnection(webServerUrl)
        return connectionOK

    @staticmethod
    def EnableDisableSubscription():
        if len(SendStatusAdapter.Instances) > 0:
            isInitialized = SendStatusAdapter.Instances[0].GetIsInitialized()

            connectionOK = SendStatusAdapter.IsConnectionOK()
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
    def TestConnection(webServerUrl):
        try:
            URL = webServerUrl + "/api/v1/ping"
            r = requests.get(url=URL, timeout=1, headers={}, verify=False)
            data = r.json()
            logging.info(data)
            return data['code'] == 0
        except Exception as ex:
            SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::TestConnection() " + webServerUrl + " Exception: " + str(ex))
            return False

    @staticmethod
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1

    # messageData is a tuple of bytearrays
    def SendData(self, messageData, successCB, failureCB, notSentCB, callbackQueue, settingsDictionary):
        try:
            if settingsDictionary["WebServerUrl"] is None:
                SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::SendData No webserver url")
                callbackQueue.put((failureCB,))
                return False

            headers = {'X-Authorization': settingsDictionary["ApiKey"]}
            thisWiRocBtAddress = SettingsClass.GetBTAddress()

            returnSuccess = True
            for data in messageData:
                # Add/Update device
                loraStatusMsg: LoraRadioMessageStatusRS = LoraRadioMessageCreator.GetStatusMessageByFullMessageData(data)
                relayPathNo: int = loraStatusMsg.GetRelayPathNo()
                btAddress = loraStatusMsg.GetBTAddress()
                device = {"BTAddress": btAddress, "headBTAddress": thisWiRocBtAddress, "relayPathNo": relayPathNo}
                URL = settingsDictionary["WebServerUrl"] + "/api/v1/Devices"
                resp = requests.post(url=URL, json=device, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData URL: {URL}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData json: {json.dumps(device)}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Response: {json.dumps(retDevice)}")
                else:
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData URL: {URL}")
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData json: {json.dumps(device)}")
                    returnSuccess = False

                # Set the device name
                if thisWiRocBtAddress == btAddress:
                    thisWiRocDeviceName = settingsDictionary["WiRocDeviceName"]
                    URL2 = settingsDictionary["WebServerUrl"] + "/api/v1/Devices/" + thisWiRocBtAddress + "/UpdateDeviceName/" + thisWiRocDeviceName
                    resp = requests.get(url=URL2, timeout=1, headers=headers, verify=False)
                    if resp.status_code == 200:
                        retDevice = resp.json()
                        SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData URL: {URL2}")
                        SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                        SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Response: {json.dumps(retDevice)}")
                    else:
                        SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData URL: {URL2}")
                        SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                        returnSuccess = False

                # Add new status
                batteryLevel: int = loraStatusMsg.GetBatteryPercent()
                siStationNumber: int = loraStatusMsg.GetSIStationNumber()
                allLoraPunchesSentOK: bool = loraStatusMsg.GetAllLoraPunchesSentOK()
                noOfLoraMsgSentNotAcked: int = loraStatusMsg.GetNoOfLoraMsgSentNotAcked()
                URL3 = settingsDictionary["WebServerUrl"] + "/api/v1/DeviceStatuses"
                deviceStatus = {"BTAddress": btAddress, "batteryLevel": batteryLevel, "siStationNumber": siStationNumber}
                #deviceStatus = {"BTAddress": btAddress, "batteryLevel": batteryLevel, "siStationNumber": siStationNumber, "allLoraPunchesSentOK": allLoraPunchesSentOK, "noOfLoraMsgSentNotAcked": noOfLoraMsgSentNotAcked}
                resp = requests.post(url=URL3, json=deviceStatus, timeout=1, headers=headers, verify=False)
                if resp.status_code == 200:
                    retDevice = resp.json()
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData URL: {URL3}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData json: {json.dumps(deviceStatus)}")
                    SendStatusAdapter.WiRocLogger.debug(f"SendStatusAdapter::SendData Response: {json.dumps(retDevice)}")
                else:
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData URL: {URL3}")
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData Headers: {json.dumps(headers)}")
                    SendStatusAdapter.WiRocLogger.error(f"SendStatusAdapter::SendData json: {json.dumps(deviceStatus)}")
                    returnSuccess = False

            if returnSuccess:
                callbackQueue.put((successCB,))
            else:
                callbackQueue.put((failureCB,))
        except Exception as ex:
            SendStatusAdapter.WiRocLogger.error("SendStatusAdapter::SendData() Exception: " + str(ex))
            callbackQueue.put((failureCB, ))
            return False
