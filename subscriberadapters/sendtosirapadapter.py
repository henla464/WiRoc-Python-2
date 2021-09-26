from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import socket
import logging


class SendToSirapAdapter(object):
    WiRocLogger = logging.getLogger('WiRoc.Output')
    Instances = []
    SubscriptionsEnabled = False

    @staticmethod
    def CreateInstances():
        if len(SendToSirapAdapter.Instances) == 0:
            SendToSirapAdapter.Instances.append(SendToSirapAdapter('sirap1'))
            return True
        # check if enabled changed => let init/enabledisablesubscription run
        isInitialized = SendToSirapAdapter.Instances[0].GetIsInitialized()
        enabled = SettingsClass.GetSendToSirapEnabled()
        subscriptionShouldBeEnabled = (isInitialized and enabled)
        if SendToSirapAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
            return True
        return False

    @staticmethod
    def GetTypeName():
        return "SIRAP"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToSirapAdapter.Instances) > 0:
            isInitialized = SendToSirapAdapter.Instances[0].GetIsInitialized()
            enabled = SettingsClass.GetSendToSirapEnabled()
            subscriptionShouldBeEnabled = (isInitialized and enabled)
            if SendToSirapAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                SendToSirapAdapter.WiRocLogger.info(
                    "SendToSirapAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                        subscriptionShouldBeEnabled))
                SendToSirapAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                DatabaseHelper.update_subscriptions(subscriptionShouldBeEnabled,
                                                    SendToSirapAdapter.GetDeleteAfterSent(),
                                                    SendToSirapAdapter.GetTypeName())

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

    def SetIsDBInitialized(self, val=True):
        self.isDBInitialized = val

    def GetTransformNames(self):
        return ["LoraSIMessageToSirapTransform", "SISIMessageToSirapTransform", "SITestTestToSirapTransform", "LoraSIMessageDoubleToSirapTransform"]

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
    def GetDelayAfterMessageSent():
        return 0

    def GetRetryDelay(self, tryNo):
        return 1

    def OpenConnection(self, failureCB, callbackQueue, settingsDictionary):
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                SendToSirapAdapter.WiRocLogger.debug(
                    "SendToSirapAdapter::SendData() Address: " + settingsDictionary["SendToSirapIP"] + " Port: " + str(
                        settingsDictionary["SendToSirapIPPort"]))
                server_address = (settingsDictionary["SendToSirapIP"], settingsDictionary["SendToSirapIPPort"])
                self.sock.settimeout(2)
                self.sock.connect(server_address)
                SendToSirapAdapter.WiRocLogger.debug("SendToSirapAdapter::SendData() After connect")
                return True
            except socket.gaierror as msg:
                SendToSirapAdapter.WiRocLogger.error(
                    "SendToSirapAdapter::SendData() Address-related error connecting to server: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                callbackQueue.put((failureCB,))
                return False
            except socket.error as msg:
                SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::SendData() Connection error: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                callbackQueue.put((failureCB,))
                return False
        return True

    # messageData is tuple of bytearray
    def SendData(self, messageData, successCB, failureCB, notSentCB, callbackQueue, settingsDictionary):
        if not self.OpenConnection(failureCB, callbackQueue, settingsDictionary):
            self.sock = None
            return False

        try:
            # Send data
            for data in messageData:
                self.sock.sendall(data)
            self.sock.close()
            self.sock = None
            SendToSirapAdapter.WiRocLogger.debug("SendToSirapAdapter::SendData() Sent to SIRAP")
            callbackQueue.put((DatabaseHelper.add_message_stat, self.GetInstanceName(), "SIMessage", "Sent", 1))
            callbackQueue.put((successCB,))
            return True
        except socket.error as msg:
            logging.error(msg)
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            callbackQueue.put((failureCB,))
            return False
        except:
            SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::SendData() Exception")
            if self.sock is not None:
                self.sock.close()
            self.sock = None
            callbackQueue.put((failureCB,))
            return False
