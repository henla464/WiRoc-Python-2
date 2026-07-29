from __future__ import annotations

from typing import Any

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import socket
import logging

from utils.utils import Utils


class SendToSirapAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSirapAdapter] = []
    SubscriptionsEnabled: bool = False

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
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
                SendToSirapAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                deleteAfterSent = SendToSirapAdapter.GetDeleteAfterSent()
                for name, transf in SendToSirapAdapter.Instances[0].transforms.items():
                    maxTries = transf.GetMaxTries()
                    SendToSirapAdapter.WiRocLogger.info(
                        "SendToSirapAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                            subscriptionShouldBeEnabled) + " name: " + name + " deleteAfterSent: " + str(deleteAfterSent) +
                        " maxTries: " + str(maxTries))
                    DatabaseHelper.update_subscription(subscriptionShouldBeEnabled, deleteAfterSent,
                                                       SendToSirapAdapter.GetTypeName(), name, maxTries)

    @staticmethod
    def EnableDisableTransforms() -> None:
        if len(SendToSirapAdapter.Instances) > 0:
            enableTransforms = SettingsClass.GetSendToSirapEnabled()
            DatabaseHelper.set_transform_enabled(enableTransforms, "LoraSIMessageToSirapTransform")
            DatabaseHelper.set_transform_enabled(enableTransforms, "SISIMessageToSirapTransform")
            DatabaseHelper.set_transform_enabled(enableTransforms, "SITestTestToSirapTransform")
            DatabaseHelper.set_transform_enabled(enableTransforms, "LoraSIMessageDoubleToSirapTransform")
            DatabaseHelper.set_transform_enabled(enableTransforms, "SRRSRRMessageToSirapTransform")

    def __init__(self, instanceName):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
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

    def GetTransform(self, transformName: str) -> Any:
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
        return 1000000  # 1 second in microseconds

    def OpenConnection(self, failureCB, settingsDictionary: dict[str, any]) -> socket.socket | None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            SendToSirapAdapter.WiRocLogger.debug(
                "SendToSirapAdapter::OpenConnection() Address: " + settingsDictionary["SendToSirapIP"] + " Port: " + str(
                    settingsDictionary["SendToSirapIPPort"]))
            server_address = (settingsDictionary["SendToSirapIP"], settingsDictionary["SendToSirapIPPort"])
            sock.settimeout(3)
            sock.connect(server_address)
            SendToSirapAdapter.WiRocLogger.debug("SendToSirapAdapter::OpenConnection() After connect")
            return sock
        except socket.gaierror as msg:
            SendToSirapAdapter.WiRocLogger.error(
                "SendToSirapAdapter::OpenConnection() Address-related error connecting to server: " + str(msg))
            sock.close()
            failureCB()
            return None
        except socket.error as msg:
            SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::OpenConnection() Connection error: " + str(msg))
            sock.close()
            failureCB()
            return None

    # messageData is tuple of bytearray
    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB, settingsDictionary: dict[str, any]) -> bool:
        try:
            for data in messageData:
                sock = self.OpenConnection(failureCB, settingsDictionary)
                if sock is None:
                    return False

                try:
                    sock.sendall(data)
                    sock.close()
                    SendToSirapAdapter.WiRocLogger.debug(
                        "SendToSirapAdapter::SendData() Sent to SIRAP: " + Utils.GetDataInHex(data, logging.DEBUG))
                except socket.error as msg:
                    logging.error(msg)
                    sock.close()
                    failureCB()
                    return False

            DatabaseHelper.add_message_stat(self.GetInstanceName(), "SIMessage", "Sent", 1)
            successCB()
            return True
        except:
            SendToSirapAdapter.WiRocLogger.error("SendToSirapAdapter::SendData() Exception")
            failureCB()
            return False
