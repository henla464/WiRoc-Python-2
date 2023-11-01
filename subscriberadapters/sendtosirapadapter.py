from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import socket
import logging
from __future__ import annotations


class SendToSirapAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSirapAdapter] = []
    SubscriptionsEnabled: bool = False

    @staticmethod
    def CreateInstances() -> bool:
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
    def GetTypeName() -> str:
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
    def EnableDisableTransforms() -> None:
        return None

    def __init__(self, instanceName):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.sock: socket.socket | None = None
        self.isInitialized: bool = False
        self.isDBInitialized: bool = False

    def GetInstanceName(self) -> str:
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    # when receiving from other WiRoc device, should we wait until the other
    # WiRoc device sent an ack to aviod sending at same time
    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

    def GetIsInitialized(self) -> bool:
        return self.isInitialized

    def ShouldBeInitialized(self) -> bool:
        return not self.isInitialized

    # has adapter, transforms, subscriptions etc been added to database?
    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return ["LoraSIMessageToSirapTransform", "SISIMessageToSirapTransform",
                "SITestTestToSirapTransform", "LoraSIMessageDoubleToSirapTransform",
                "SRRSRRMessageToSirapTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName: str) -> any:
        return self.transforms[transformName]

    def Init(self) -> bool:
        if self.GetIsInitialized():
            return True
        self.isInitialized = True
        return True

    def IsReadyToSend(self) -> bool:
        return True

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1

    def OpenConnection(self, failureCB, callbackQueue, settingsDictionary: dict[str, any]) -> bool:
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                SendToSirapAdapter.WiRocLogger.debug(
                    "SendToSirapAdapter::OpenConnection() Address: " + settingsDictionary["SendToSirapIP"] + " Port: " + str(
                        settingsDictionary["SendToSirapIPPort"]))
                server_address = (settingsDictionary["SendToSirapIP"], settingsDictionary["SendToSirapIPPort"])
                self.sock.settimeout(2)
                self.sock.connect(server_address)
                SendToSirapAdapter.WiRocLogger.debug("SendToSirapAdapter::OpenConnection() After connect")
                return True
            except socket.gaierror as msg:
                SendToSirapAdapter.WiRocLogger.error(
                    "SendToSirapAdapter::OpenConnection() Address-related error connecting to server: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                callbackQueue.put((failureCB,))
                return False
            except socket.error as msg:
                SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::OpenConnection() Connection error: " + str(msg))
                if self.sock is not None:
                    self.sock.close()
                self.sock = None
                callbackQueue.put((failureCB,))
                return False
        return True

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB, callbackQueue, settingsDictionary: dict[str, any]) -> bool:
        try:
            # Send data
            for data in messageData:
                if not self.OpenConnection(failureCB, callbackQueue, settingsDictionary):
                    self.sock = None
                    return False

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
