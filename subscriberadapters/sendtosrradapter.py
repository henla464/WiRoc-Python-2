from __future__ import annotations
from typing import Any

from chipGPIO.hardwareAbstraction import HardwareAbstraction
from settings.settings import SettingsClass
from datamodel.db_helper import DatabaseHelper
import logging
from srrradio import SRRRadio


class SendToSRRAdapter(object):
    WiRocLogger: logging.Logger = logging.getLogger('WiRoc.Output')
    Instances: list[SendToSRRAdapter] = []
    SubscriptionsEnabled: bool = False

    @staticmethod
    def CreateInstances(hardwareAbstraction: HardwareAbstraction) -> bool:
        if hardwareAbstraction.HasSRR():
            if len(SendToSRRAdapter.Instances) == 0:

                if SettingsClass.GetSRRMode() == "SEND" and (
                        SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled()):

                    srrRadio = SRRRadio.GetInstance(hardwareAbstraction)
                    if srrRadio is not None:
                        SendToSRRAdapter.Instances.append(
                            SendToSRRAdapter("sndsrr1", srrRadio))
                        return True
                    return False
                else:
                    SendToSRRAdapter.Instances = []
                    return False
            else:
                if SettingsClass.GetSRRMode() == "SEND" and (
                        SettingsClass.GetSRRRedChannelEnabled() or SettingsClass.GetSRRBlueChannelEnabled()):
                    return False
                else:
                    SendToSRRAdapter.Instances = []
                    return True
        return False

    @staticmethod
    def GetTypeName() -> str:
        return "SRR"

    @staticmethod
    def EnableDisableSubscription():
        if len(SendToSRRAdapter.Instances) > 0:
            isInitialized = SendToSRRAdapter.Instances[0].GetIsInitialized()
            enabled = (SettingsClass.GetSRREnabled() and SettingsClass.GetSRRMode() == "SEND")
            subscriptionShouldBeEnabled = (isInitialized and enabled)
            if SendToSRRAdapter.SubscriptionsEnabled != subscriptionShouldBeEnabled:
                SendToSRRAdapter.SubscriptionsEnabled = subscriptionShouldBeEnabled
                deleteAfterSent = SendToSRRAdapter.GetDeleteAfterSent()
                for name, transf in SendToSRRAdapter.Instances[0].transforms.items():
                    maxTries = transf.GetMaxTries()
                    SendToSRRAdapter.WiRocLogger.info(
                        "SendToSRRAdapter::EnableDisableSubscription() subscription set enabled: " + str(
                            subscriptionShouldBeEnabled) + " name: " + name + " deleteAfterSent: " + str(deleteAfterSent) +
                        " maxTries: " + str(maxTries))
                    DatabaseHelper.update_subscription(subscriptionShouldBeEnabled, deleteAfterSent,
                                                       SendToSRRAdapter.GetTypeName(), name, maxTries)

    @staticmethod
    def EnableDisableTransforms() -> None:
        if len(SendToSRRAdapter.Instances) > 0:
            enableSendTransforms = (SettingsClass.GetSRREnabled() and SettingsClass.GetSRRMode() == "SEND")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "LoraSIMessageToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "SISIMessageToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "SITestTestToSRRTransform")
            DatabaseHelper.set_transform_enabled(enableSendTransforms, "LoraSIMessageDoubleToSRRTransform")

    def __init__(self, instanceName: str, srrRadio: SRRRadio):
        self.instanceName: str = instanceName
        self.transforms: dict[str, any] = {}
        self.isDBInitialized: bool = False
        self.srrRadio: SRRRadio = srrRadio

    def GetInstanceName(self) -> str:
        return self.instanceName

    @staticmethod
    def GetDeleteAfterSent() -> bool:
        return True

    @staticmethod
    def GetWaitUntilAckSent() -> bool:
        return False

    def GetIsInitialized(self) -> bool:
        return self.srrRadio.GetIsInitialized(
            SettingsClass.GetSRREnabled(), SettingsClass.GetSRRMode(),
            SettingsClass.GetSRRRedChannelEnabled(), SettingsClass.GetSRRRedChannelListenOnly(),
            SettingsClass.GetSRRBlueChannelEnabled(), SettingsClass.GetSRRBlueChannelListenOnly())

    def ShouldBeInitialized(self) -> bool:
        return not self.GetIsInitialized()

    def GetIsDBInitialized(self) -> bool:
        return self.isDBInitialized

    def SetIsDBInitialized(self, val: bool = True) -> None:
        self.isDBInitialized = val

    def GetTransformNames(self) -> list[str]:
        return ["LoraSIMessageToSRRTransform", "SISIMessageToSRRTransform",
                "SITestTestToSRRTransform", "LoraSIMessageDoubleToSRRTransform"]

    def SetTransform(self, transformClass):
        self.transforms[transformClass.GetName()] = transformClass

    def GetTransform(self, transformName: str) -> Any:
        return self.transforms[transformName]

    def Init(self) -> bool:
        return self.srrRadio.Init(
            SettingsClass.GetSRREnabled(), SettingsClass.GetSRRMode(),
            SettingsClass.GetSRRRedChannelEnabled(), SettingsClass.GetSRRRedChannelListenOnly(),
            SettingsClass.GetSRRBlueChannelEnabled(), SettingsClass.GetSRRBlueChannelListenOnly())

    def IsReadyToSend(self) -> bool:
        return True

    @staticmethod
    def GetDelayAfterMessageSent() -> float:
        return 0

    def GetRetryDelay(self, tryNo: int) -> float:
        return 1

    def SendData(self, messageData: tuple[bytearray], successCB, failureCB, notSentCB,
                 settingsDictionary: dict[str, any]) -> bool:
        try:
            for data in messageData:
                self.srrRadio.SendData(data)
            successCB()
            return True
        except Exception as e:
            self.WiRocLogger.error(f"SendData: Exception - {str(e)}")
            failureCB()
            return False
